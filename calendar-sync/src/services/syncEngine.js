const { v4: uuidv4 } = require('uuid');
const db = require('../models/database');
const googleCalendar = require('./googleCalendar');
const frontdeskClient = require('./frontdeskClient');
const privacyFilter = require('./privacyFilter');

/**
 * Sync Engine
 *
 * Handles bidirectional synchronization between calendars.
 * Maintains event mappings and handles conflict resolution.
 */

/**
 * Create privacy-filtered title for Google Calendar
 * Format: "FirstName XX" (just first name + last 2 digits of phone)
 * Example: "David 67"
 *
 * Note: We intentionally leave out action/metal for privacy.
 * The full details stay in the main Front Desk calendar.
 */
function createGoogleTitle(event) {
  const firstName = privacyFilter.extractFirstName(event.customerName || event.customer);
  const lastTwo = privacyFilter.extractLastTwoDigits(event.customerPhone || event.phone);

  return `${firstName} ${lastTwo}`;
}

/**
 * Sync a Front Desk event to Google Calendar
 * @param {Object} frontdeskEvent - Event from Front Desk
 * @returns {Object} Sync result with mapping
 */
async function syncFrontdeskToGoogle(frontdeskEvent) {
  const mappingId = uuidv4();

  // Check if already synced
  const existing = db
    .prepare('SELECT * FROM event_mappings WHERE frontdesk_event_id = ?')
    .get(frontdeskEvent.id);

  if (existing) {
    // Update existing Google event
    return await updateGoogleFromFrontdesk(existing, frontdeskEvent);
  }

  // Create privacy-filtered event for Google
  const googleTitle = createGoogleTitle(frontdeskEvent);
  const googleEventData = {
    summary: googleTitle,
    start: {
      dateTime: frontdeskEvent.startTime || frontdeskEvent.dateTime,
      timeZone: 'America/New_York',
    },
    end: {
      dateTime: frontdeskEvent.endTime,
      timeZone: 'America/New_York',
    },
    description: frontdeskEvent.purpose || '',
    extendedProperties: {
      private: {
        syncSource: 'frontdesk',
        frontdeskId: frontdeskEvent.id,
        lastTwo: privacyFilter.extractLastTwoDigits(frontdeskEvent.customerPhone || frontdeskEvent.phone),
      },
    },
  };

  try {
    const googleEvent = await googleCalendar.createEvent(googleEventData);

    // Store mapping
    db.prepare(`
      INSERT INTO event_mappings (
        id, frontdesk_event_id, google_event_id, google_title,
        original_customer_name, original_phone_last_two,
        event_start, event_end, sync_status, last_synced_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'synced', datetime('now'))
    `).run(
      mappingId,
      frontdeskEvent.id,
      googleEvent.id,
      googleTitle,
      frontdeskEvent.customerName || frontdeskEvent.customer,
      privacyFilter.extractLastTwoDigits(frontdeskEvent.customerPhone || frontdeskEvent.phone),
      frontdeskEvent.startTime || frontdeskEvent.dateTime,
      frontdeskEvent.endTime
    );

    // Log success
    logSync('create', 'frontdesk', frontdeskEvent.id, { googleEventId: googleEvent.id }, true);

    return {
      success: true,
      mappingId,
      googleEventId: googleEvent.id,
      filteredTitle: googleTitle,
    };
  } catch (error) {
    logSync('create', 'frontdesk', frontdeskEvent.id, { error: error.message }, false, error.message);
    throw error;
  }
}

/**
 * Update Google event from Front Desk changes
 */
async function updateGoogleFromFrontdesk(mapping, frontdeskEvent) {
  const googleTitle = createGoogleTitle(frontdeskEvent);
  const googleEventData = {
    summary: googleTitle,
    start: {
      dateTime: frontdeskEvent.startTime || frontdeskEvent.dateTime,
      timeZone: 'America/New_York',
    },
    end: {
      dateTime: frontdeskEvent.endTime,
      timeZone: 'America/New_York',
    },
    description: frontdeskEvent.purpose || '',
  };

  try {
    await googleCalendar.updateEvent(mapping.google_event_id, googleEventData);

    // Update mapping
    db.prepare(`
      UPDATE event_mappings
      SET google_title = ?, event_start = ?, event_end = ?,
          sync_status = 'synced', last_synced_at = datetime('now'), updated_at = datetime('now')
      WHERE id = ?
    `).run(googleTitle, frontdeskEvent.startTime, frontdeskEvent.endTime, mapping.id);

    logSync('update', 'frontdesk', frontdeskEvent.id, { googleEventId: mapping.google_event_id }, true);

    return {
      success: true,
      mappingId: mapping.id,
      googleEventId: mapping.google_event_id,
      filteredTitle: googleTitle,
    };
  } catch (error) {
    db.prepare(`
      UPDATE event_mappings SET sync_status = 'error', last_sync_error = ? WHERE id = ?
    `).run(error.message, mapping.id);

    logSync('update', 'frontdesk', frontdeskEvent.id, { error: error.message }, false, error.message);
    throw error;
  }
}

/**
 * Sync a Google Calendar event to Front Desk
 * @param {Object} googleEvent - Event from Google Calendar
 * @returns {Object} Sync result
 */
async function syncGoogleToFrontdesk(googleEvent) {
  // Check if this is a synced event (created from Front Desk)
  const extProps = googleEvent.extendedProperties?.private || {};
  if (extProps.syncSource === 'frontdesk') {
    console.log(`[Sync] Skipping event ${googleEvent.id} - originated from Front Desk`);
    return { success: true, skipped: true, reason: 'originated_from_frontdesk' };
  }

  // Check if already mapped
  const existing = db
    .prepare('SELECT * FROM event_mappings WHERE google_event_id = ?')
    .get(googleEvent.id);

  if (existing) {
    // Update existing Front Desk event
    return await updateFrontdeskFromGoogle(existing, googleEvent);
  }

  // Create new event in Front Desk
  // Parse any info we can from the Google event title
  const parsed = privacyFilter.parseFilteredTitle(googleEvent.summary);

  const frontdeskEventData = {
    customer: parsed.firstName || googleEvent.summary || 'Google Calendar Event',
    phone: '', // Can't recover full phone from Google
    dateTime: googleEvent.start?.dateTime || googleEvent.start?.date,
    endTime: googleEvent.end?.dateTime || googleEvent.end?.date,
    purpose: googleEvent.description || '',
    notes: `Synced from Google Calendar (${googleEvent.id})`,
    source: 'google',
    googleEventId: googleEvent.id,
  };

  try {
    const frontdeskEvent = await frontdeskClient.createEvent(frontdeskEventData);
    const mappingId = uuidv4();

    // Store mapping
    db.prepare(`
      INSERT INTO event_mappings (
        id, frontdesk_event_id, google_event_id, google_title,
        event_start, event_end, sync_status, last_synced_at
      ) VALUES (?, ?, ?, ?, ?, ?, 'synced', datetime('now'))
    `).run(
      mappingId,
      frontdeskEvent.id,
      googleEvent.id,
      googleEvent.summary,
      googleEvent.start?.dateTime || googleEvent.start?.date,
      googleEvent.end?.dateTime || googleEvent.end?.date
    );

    logSync('create', 'google', googleEvent.id, { frontdeskId: frontdeskEvent.id }, true);

    return {
      success: true,
      mappingId,
      frontdeskEventId: frontdeskEvent.id,
    };
  } catch (error) {
    logSync('create', 'google', googleEvent.id, { error: error.message }, false, error.message);
    throw error;
  }
}

/**
 * Update Front Desk event from Google changes
 */
async function updateFrontdeskFromGoogle(mapping, googleEvent) {
  const updates = {
    dateTime: googleEvent.start?.dateTime || googleEvent.start?.date,
    endTime: googleEvent.end?.dateTime || googleEvent.end?.date,
    purpose: googleEvent.description || undefined,
  };

  try {
    await frontdeskClient.updateEvent(mapping.frontdesk_event_id, updates);

    db.prepare(`
      UPDATE event_mappings
      SET event_start = ?, event_end = ?, google_title = ?,
          sync_status = 'synced', last_synced_at = datetime('now'), updated_at = datetime('now')
      WHERE id = ?
    `).run(updates.dateTime, updates.endTime, googleEvent.summary, mapping.id);

    logSync('update', 'google', googleEvent.id, { frontdeskId: mapping.frontdesk_event_id }, true);

    return {
      success: true,
      mappingId: mapping.id,
      frontdeskEventId: mapping.frontdesk_event_id,
    };
  } catch (error) {
    db.prepare(`
      UPDATE event_mappings SET sync_status = 'error', last_sync_error = ? WHERE id = ?
    `).run(error.message, mapping.id);

    logSync('update', 'google', googleEvent.id, { error: error.message }, false, error.message);
    throw error;
  }
}

/**
 * Delete event from all synced calendars
 * @param {string} source - Which calendar initiated the delete ('frontdesk' or 'google')
 * @param {string} eventId - Event ID from the source
 */
async function syncDelete(source, eventId) {
  const column = source === 'frontdesk' ? 'frontdesk_event_id' : 'google_event_id';
  const mapping = db.prepare(`SELECT * FROM event_mappings WHERE ${column} = ?`).get(eventId);

  if (!mapping) {
    console.log(`[Sync] No mapping found for ${source} event ${eventId}`);
    return { success: true, noMapping: true };
  }

  try {
    // Delete from the other calendar
    if (source === 'frontdesk' && mapping.google_event_id) {
      await googleCalendar.deleteEvent(mapping.google_event_id);
    } else if (source === 'google' && mapping.frontdesk_event_id) {
      await frontdeskClient.deleteEvent(mapping.frontdesk_event_id);
    }

    // Remove mapping
    db.prepare('DELETE FROM event_mappings WHERE id = ?').run(mapping.id);

    logSync('delete', source, eventId, { mappingId: mapping.id }, true);

    return { success: true, mappingId: mapping.id };
  } catch (error) {
    logSync('delete', source, eventId, { error: error.message }, false, error.message);
    throw error;
  }
}

/**
 * Get mapping by event ID
 * @param {string} source - 'frontdesk' or 'google'
 * @param {string} eventId - Event ID
 * @returns {Object|null} Mapping record
 */
function getMapping(source, eventId) {
  const column = source === 'frontdesk' ? 'frontdesk_event_id' : 'google_event_id';
  return db.prepare(`SELECT * FROM event_mappings WHERE ${column} = ?`).get(eventId);
}

/**
 * Get all mappings
 * @returns {Array} All event mappings
 */
function getAllMappings() {
  return db.prepare('SELECT * FROM event_mappings ORDER BY created_at DESC').all();
}

/**
 * Get sync statistics
 * @returns {Object} Sync stats
 */
function getStats() {
  const total = db.prepare('SELECT COUNT(*) as count FROM event_mappings').get().count;
  const synced = db
    .prepare("SELECT COUNT(*) as count FROM event_mappings WHERE sync_status = 'synced'")
    .get().count;
  const errors = db
    .prepare("SELECT COUNT(*) as count FROM event_mappings WHERE sync_status = 'error'")
    .get().count;
  const recentLogs = db
    .prepare('SELECT * FROM sync_log ORDER BY created_at DESC LIMIT 10')
    .all();

  return {
    totalMappings: total,
    synced,
    errors,
    recentActivity: recentLogs,
    googleConnected: googleCalendar.isAuthenticated(),
  };
}

/**
 * Log sync activity
 */
function logSync(action, source, eventId, details, success, errorMessage = null) {
  db.prepare(`
    INSERT INTO sync_log (action, source, event_id, details, success, error_message)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(action, source, eventId, JSON.stringify(details), success ? 1 : 0, errorMessage);
}

/**
 * Full sync - reconcile all events between calendars
 * @param {Object} options - Sync options
 * @param {string} options.startDate - Start of date range
 * @param {string} options.endDate - End of date range
 */
async function fullSync(options = {}) {
  const results = {
    frontdeskToGoogle: { created: 0, updated: 0, errors: [] },
    googleToFrontdesk: { created: 0, updated: 0, errors: [] },
  };

  // Default to syncing next 30 days
  const startDate = options.startDate || new Date().toISOString();
  const endDate =
    options.endDate || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();

  console.log(`[Sync] Starting full sync from ${startDate} to ${endDate}`);

  // Sync Front Desk → Google
  try {
    const frontdeskEvents = await frontdeskClient.getEvents({ startDate, endDate });
    for (const event of frontdeskEvents) {
      try {
        const result = await syncFrontdeskToGoogle(event);
        if (result.success && !result.skipped) {
          const mapping = getMapping('frontdesk', event.id);
          if (mapping?.created_at === mapping?.updated_at) {
            results.frontdeskToGoogle.created++;
          } else {
            results.frontdeskToGoogle.updated++;
          }
        }
      } catch (error) {
        results.frontdeskToGoogle.errors.push({ eventId: event.id, error: error.message });
      }
    }
  } catch (error) {
    console.error('[Sync] Failed to get Front Desk events:', error.message);
  }

  // Sync Google → Front Desk
  try {
    const googleEvents = await googleCalendar.listEvents({
      timeMin: startDate,
      timeMax: endDate,
    });
    for (const event of googleEvents) {
      try {
        const result = await syncGoogleToFrontdesk(event);
        if (result.success && !result.skipped) {
          const mapping = getMapping('google', event.id);
          if (mapping?.created_at === mapping?.updated_at) {
            results.googleToFrontdesk.created++;
          } else {
            results.googleToFrontdesk.updated++;
          }
        }
      } catch (error) {
        results.googleToFrontdesk.errors.push({ eventId: event.id, error: error.message });
      }
    }
  } catch (error) {
    console.error('[Sync] Failed to get Google events:', error.message);
  }

  console.log('[Sync] Full sync complete:', results);
  return results;
}

module.exports = {
  syncFrontdeskToGoogle,
  syncGoogleToFrontdesk,
  syncDelete,
  getMapping,
  getAllMappings,
  getStats,
  fullSync,
  createGoogleTitle,
};
