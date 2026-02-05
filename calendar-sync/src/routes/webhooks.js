const { Router } = require('express');
const crypto = require('crypto');
const env = require('../config/env');
const db = require('../models/database');
const syncEngine = require('../services/syncEngine');
const googleCalendar = require('../services/googleCalendar');
const frontdeskClient = require('../services/frontdeskClient');
const { v4: uuidv4 } = require('uuid');

const router = Router();

/**
 * Detect buy/sell action from text (purpose, reason, transcript)
 * @param {string} text - Text to analyze
 * @returns {string|null} 'buy', 'sell', or null
 */
function detectActionFromText(text) {
  if (!text) return null;
  const lower = text.toLowerCase();

  // Check for sell indicators first (customer selling to us = we buy)
  if (lower.includes('sell') || lower.includes('selling') || lower.includes('liquidat')) {
    return 'sell';
  }
  // Check for buy indicators (customer buying from us = we sell)
  if (lower.includes('buy') || lower.includes('buying') || lower.includes('purchas')) {
    return 'buy';
  }
  return null;
}

/**
 * Detect metal type from text
 * @param {string} text - Text to analyze
 * @returns {string|null} 'gold', 'silver', 'platinum', 'palladium', or null
 */
function detectMetalFromText(text) {
  if (!text) return null;
  const lower = text.toLowerCase();

  if (lower.includes('gold') || lower.includes('au ')) return 'gold';
  if (lower.includes('silver') || lower.includes('ag ')) return 'silver';
  if (lower.includes('platinum') || lower.includes('pt ')) return 'platinum';
  if (lower.includes('palladium') || lower.includes('pd ')) return 'palladium';
  return null;
}

/**
 * Detect quantity (oz) from text
 * @param {string} text - Text to analyze
 * @returns {number|null} Quantity in oz or null
 */
function detectQuantityFromText(text) {
  if (!text) return null;

  // Look for patterns like "2 oz", "10 ounce", "5oz", "1/2 oz"
  const patterns = [
    /(\d+(?:\.\d+)?)\s*(?:oz|ounce)/i,
    /(\d+)\s*\/\s*(\d+)\s*(?:oz|ounce)/i,  // fractions like 1/2 oz
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      if (match[2]) {
        // Fraction
        return parseFloat(match[1]) / parseFloat(match[2]);
      }
      return parseFloat(match[1]);
    }
  }
  return null;
}

/**
 * Verify webhook signature (for Front Desk webhooks)
 */
function verifyWebhookSignature(req) {
  if (!env.WEBHOOK_SECRET) {
    return true; // No secret configured, skip verification
  }

  const signature = req.headers['x-webhook-signature'];
  if (!signature) {
    return false;
  }

  const payload = JSON.stringify(req.body);
  const expectedSignature = crypto
    .createHmac('sha256', env.WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}

/**
 * POST /api/webhook/frontdesk
 * Receive event notifications from Front Desk calendar
 *
 * Body: {
 *   event: 'event.created' | 'event.updated' | 'event.deleted',
 *   data: { ... event data ... }
 * }
 */
router.post('/frontdesk', async (req, res, next) => {
  try {
    // Verify signature
    if (!verifyWebhookSignature(req)) {
      console.warn('[Webhook] Invalid signature from Front Desk');
      return res.status(401).json({ error: 'Invalid signature' });
    }

    const { event: eventType, data } = req.body;
    console.log(`[Webhook] Front Desk: ${eventType}`);

    if (!googleCalendar.isAuthenticated()) {
      console.warn('[Webhook] Google Calendar not connected, skipping sync');
      return res.json({ received: true, synced: false, reason: 'google_not_connected' });
    }

    let result;

    switch (eventType) {
      case 'event.created':
      case 'event.updated':
        result = await syncEngine.syncFrontdeskToGoogle(data);
        break;

      case 'event.deleted':
        result = await syncEngine.syncDelete('frontdesk', data.id);
        break;

      default:
        console.log(`[Webhook] Unknown event type: ${eventType}`);
        return res.json({ received: true, synced: false, reason: 'unknown_event_type' });
    }

    res.json({ received: true, synced: true, result });
  } catch (err) {
    console.error('[Webhook] Front Desk error:', err.message);
    // Always return 200 to prevent retries for non-recoverable errors
    res.json({ received: true, synced: false, error: err.message });
  }
});

/**
 * POST /api/webhook/google
 * Receive push notifications from Google Calendar
 *
 * Google sends notifications when calendar changes.
 * We then fetch the changed events and sync them.
 */
router.post('/google', async (req, res, next) => {
  try {
    // Google sends a sync notification first, then change notifications
    const channelId = req.headers['x-goog-channel-id'];
    const resourceState = req.headers['x-goog-resource-state'];
    const resourceId = req.headers['x-goog-resource-id'];

    console.log(`[Webhook] Google: state=${resourceState}, channel=${channelId}`);

    // Acknowledge immediately (Google expects quick response)
    res.status(200).send('OK');

    // Skip sync notification (sent when watch is set up)
    if (resourceState === 'sync') {
      console.log('[Webhook] Google sync notification, skipping');
      return;
    }

    // Handle exists (calendar changed) notification
    if (resourceState === 'exists') {
      // Fetch recent events and sync changes
      // Google doesn't tell us exactly what changed, so we do incremental sync
      const now = new Date();
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      const oneDayFromNow = new Date(now.getTime() + 24 * 60 * 60 * 1000);

      try {
        const events = await googleCalendar.listEvents({
          timeMin: oneHourAgo.toISOString(),
          timeMax: oneDayFromNow.toISOString(),
          maxResults: 50,
        });

        for (const event of events) {
          try {
            await syncEngine.syncGoogleToFrontdesk(event);
          } catch (err) {
            console.error(`[Webhook] Failed to sync Google event ${event.id}:`, err.message);
          }
        }
      } catch (err) {
        console.error('[Webhook] Failed to fetch Google events:', err.message);
      }
    }
  } catch (err) {
    console.error('[Webhook] Google error:', err.message);
    // Already sent response, just log
  }
});

/**
 * POST /api/webhook/google/setup
 * Set up Google Calendar push notifications
 *
 * Body: { webhookUrl: 'https://your-domain.com/api/webhook/google' }
 */
router.post('/google/setup', async (req, res, next) => {
  try {
    if (!googleCalendar.isAuthenticated()) {
      return res.status(503).json({
        error: 'Google Calendar not connected',
        authUrl: '/api/auth/google',
      });
    }

    const { webhookUrl } = req.body;

    if (!webhookUrl) {
      return res.status(400).json({ error: 'Missing webhookUrl' });
    }

    const channel = await googleCalendar.setupPushNotifications(webhookUrl);
    res.json({
      success: true,
      channel,
      expiresAt: new Date(parseInt(channel.expiration)).toISOString(),
    });
  } catch (err) {
    next(err);
  }
});

/**
 * POST /api/webhook/external
 * Receive notifications from external Frontdesk systems (e.g., MyAI Front Desk)
 *
 * Handles multiple formats:
 * - Standard: { event: 'appointment.created', data: { ... } }
 * - MyAIFrontDesk: { call_id, caller_number, appointment_time, ... }
 * - Flat: { id, name, phone, start, ... }
 *
 * Creates appointments directly in OpenTruth Front Desk calendar,
 * and optionally syncs to Google Calendar if connected.
 */
router.post('/external', async (req, res, next) => {
  try {
    // Log raw incoming data for debugging
    console.log(`[Webhook] External raw data:`, JSON.stringify(req.body, null, 2));

    const body = req.body;
    let eventType = 'appointment.created'; // Default to created
    let eventData = {};

    // Handle different formats
    if (body.event && body.data) {
      // Standard format: { event: '...', data: { ... } }
      eventType = body.event;
      eventData = body.data;
    } else if (body.call_id || body.caller_number || body.appointment_time) {
      // MyAIFrontDesk format
      eventType = body.status === 'cancelled' ? 'appointment.cancelled' : 'appointment.created';
      const purpose = body.reason || body.purpose || body.service || body.call_summary || 'Appointment';
      eventData = {
        id: body.call_id || body.id || `ext-${Date.now()}`,
        customerName: body.caller_name || body.name || body.customer_name || 'Customer',
        customerPhone: body.caller_number || body.phone || body.customer_phone || '',
        startTime: body.appointment_time || body.scheduled_time || body.start_time || body.datetime,
        endTime: body.end_time || body.appointment_end,
        purpose: purpose,
        notes: body.notes || body.transcript || body.call_notes || '',
        // Buy/sell action - check explicit field or detect from purpose
        action: body.action || detectActionFromText(purpose),
        // Metal/product type
        metal: body.metal || body.product || detectMetalFromText(purpose),
        quantity: body.quantity || body.amount || body.oz || detectQuantityFromText(purpose),
      };
    } else {
      // Flat format - try to extract what we can
      const purpose = body.purpose || body.service || body.reason || body.type || 'Appointment';
      eventData = {
        id: body.id || body.appointmentId || body.appointment_id || `ext-${Date.now()}`,
        customerName: body.customerName || body.customer_name || body.name || body.caller || 'Customer',
        customerPhone: body.customerPhone || body.customer_phone || body.phone || body.caller_number || '',
        startTime: body.startTime || body.start_time || body.datetime || body.appointment_time || body.start,
        endTime: body.endTime || body.end_time || body.end,
        purpose: purpose,
        notes: body.notes || '',
        action: body.action || detectActionFromText(purpose),
        metal: body.metal || body.product || detectMetalFromText(purpose),
        quantity: body.quantity || body.amount || body.oz || detectQuantityFromText(purpose),
      };
    }

    console.log(`[Webhook] External parsed: type=${eventType}, name=${eventData.customerName}, phone=${eventData.customerPhone}, action=${eventData.action || 'unknown'}, metal=${eventData.metal || 'unknown'}, qty=${eventData.quantity || 'unknown'}`);

    const results = {
      frontdesk: null,
      google: null,
    };

    // Handle cancellations/deletions
    if (eventType.includes('cancel') || eventType.includes('delet')) {
      // Delete from Front Desk and Google
      try {
        await frontdeskClient.deleteEvent(eventData.id);
        results.frontdesk = { deleted: true };
      } catch (err) {
        console.error('[Webhook] Failed to delete from Front Desk:', err.message);
        results.frontdesk = { error: err.message };
      }

      if (googleCalendar.isAuthenticated()) {
        try {
          results.google = await syncEngine.syncDelete('frontdesk', eventData.id);
        } catch (err) {
          console.error('[Webhook] Failed to delete from Google:', err.message);
          results.google = { error: err.message };
        }
      }
    } else {
      // Create/Update appointment
      // Calculate endTime if not provided (default to startTime + 30 minutes)
      let endTime = eventData.endTime;
      if (!endTime && eventData.startTime) {
        const startDate = new Date(eventData.startTime);
        const endDate = new Date(startDate.getTime() + 30 * 60 * 1000);
        endTime = endDate.toISOString().replace('Z', '').split('.')[0];
      }

      // Check if we already have a mapping for this external ID
      const existingMapping = db
        .prepare('SELECT * FROM event_mappings WHERE external_event_id = ?')
        .get(eventData.id);

      const frontdeskEventData = {
        customer: eventData.customerName,
        phone: eventData.customerPhone,
        dateTime: eventData.startTime,
        endTime: endTime,
        purpose: eventData.purpose,
        notes: `${eventData.notes || ''}\nSource: MyAIFrontDesk (${eventData.id})`.trim(),
        source: 'myaifrontdesk',
        externalId: eventData.id,
        // Matching fields - buy/sell bullion
        action: eventData.action,      // 'buy' or 'sell'
        metal: eventData.metal,        // 'gold', 'silver', 'platinum', 'palladium'
        quantity: eventData.quantity,  // oz amount
      };

      try {
        let frontdeskResult;
        let isUpdate = false;

        if (existingMapping && existingMapping.frontdesk_event_id) {
          // Update existing appointment
          console.log(`[Webhook] Updating existing appointment: ${existingMapping.frontdesk_event_id}`);
          await frontdeskClient.updateEvent(existingMapping.frontdesk_event_id, frontdeskEventData);
          frontdeskResult = { id: existingMapping.frontdesk_event_id };
          results.frontdesk = { updated: true, id: existingMapping.frontdesk_event_id };
          isUpdate = true;

          // Update mapping timestamps
          db.prepare(`
            UPDATE event_mappings
            SET event_start = ?, event_end = ?, updated_at = datetime('now'),
                sync_status = 'synced', last_synced_at = datetime('now')
            WHERE id = ?
          `).run(eventData.startTime, endTime, existingMapping.id);
        } else {
          // Create new appointment
          frontdeskResult = await frontdeskClient.createEvent(frontdeskEventData);
          console.log(`[Webhook] Created appointment in Front Desk: ${frontdeskResult.id}`);
          results.frontdesk = { created: true, id: frontdeskResult.id };

          // Store mapping for future updates
          const mappingId = uuidv4();
          db.prepare(`
            INSERT INTO event_mappings (
              id, frontdesk_event_id, external_event_id,
              original_customer_name, original_phone_last_two,
              event_start, event_end, sync_status, last_synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'synced', datetime('now'))
          `).run(
            mappingId,
            frontdeskResult.id,
            eventData.id,
            eventData.customerName,
            eventData.customerPhone?.slice(-2) || '',
            eventData.startTime,
            endTime
          );
        }

        // Step 2: Optionally sync to Google Calendar with privacy filtering
        if (googleCalendar.isAuthenticated()) {
          try {
            const mappedEvent = {
              id: frontdeskResult.id || eventData.id,
              customerName: eventData.customerName,
              customerPhone: eventData.customerPhone,
              startTime: eventData.startTime,
              endTime: endTime,
              purpose: eventData.purpose,
              source: 'external',
            };
            const googleResult = await syncEngine.syncFrontdeskToGoogle(mappedEvent);
            console.log(`[Webhook] ${isUpdate ? 'Updated' : 'Synced'} to Google Calendar:`, googleResult);
            results.google = googleResult;
          } catch (err) {
            console.error('[Webhook] Failed to sync to Google:', err.message);
            results.google = { error: err.message };
          }
        } else {
          console.log('[Webhook] Google Calendar not connected, skipping Google sync');
          results.google = { skipped: true, reason: 'google_not_connected' };
        }
      } catch (err) {
        console.error('[Webhook] Failed to create/update in Front Desk:', err.message);
        results.frontdesk = { error: err.message };
      }
    }

    console.log(`[Webhook] External sync results:`, results);
    res.json({
      received: true,
      synced: results.frontdesk?.created || results.frontdesk?.updated || results.frontdesk?.deleted || false,
      results,
    });
  } catch (err) {
    console.error('[Webhook] External error:', err.message);
    res.json({ received: true, synced: false, error: err.message });
  }
});

module.exports = router;
