const { google } = require('googleapis');
const env = require('../config/env');
const db = require('../models/database');

/**
 * Google Calendar Service
 *
 * Handles OAuth2 authentication and Calendar API operations.
 */

// Create OAuth2 client
const oauth2Client = new google.auth.OAuth2(
  env.GOOGLE_CLIENT_ID,
  env.GOOGLE_CLIENT_SECRET,
  env.GOOGLE_REDIRECT_URI
);

// Calendar API instance
let calendar = null;

/**
 * Initialize calendar with stored tokens
 */
function initializeFromStoredTokens() {
  const row = db.prepare('SELECT * FROM google_tokens WHERE id = 1').get();

  if (row && row.access_token) {
    oauth2Client.setCredentials({
      access_token: row.access_token,
      refresh_token: row.refresh_token,
      expiry_date: row.expiry_date,
      scope: row.scope,
    });
    calendar = google.calendar({ version: 'v3', auth: oauth2Client });
    console.log('[Google] Initialized from stored tokens');
    return true;
  }

  console.log('[Google] No stored tokens found');
  return false;
}

/**
 * Generate OAuth2 authorization URL
 * @returns {string} URL to redirect user for authorization
 */
function getAuthUrl() {
  const scopes = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly',
  ];

  return oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: scopes,
    prompt: 'consent', // Force refresh token generation
  });
}

/**
 * Exchange authorization code for tokens
 * @param {string} code - Authorization code from OAuth callback
 * @returns {Object} Token response
 */
async function exchangeCodeForTokens(code) {
  const { tokens } = await oauth2Client.getToken(code);
  oauth2Client.setCredentials(tokens);

  // Store tokens in database
  db.prepare(`
    INSERT OR REPLACE INTO google_tokens (id, access_token, refresh_token, expiry_date, scope, updated_at)
    VALUES (1, ?, ?, ?, ?, datetime('now'))
  `).run(
    tokens.access_token,
    tokens.refresh_token,
    tokens.expiry_date,
    tokens.scope
  );

  calendar = google.calendar({ version: 'v3', auth: oauth2Client });
  console.log('[Google] Tokens stored successfully');

  return tokens;
}

/**
 * Check if we have valid credentials
 * @returns {boolean} True if authenticated
 */
function isAuthenticated() {
  return calendar !== null;
}

/**
 * Refresh access token if needed
 */
async function refreshTokenIfNeeded() {
  const credentials = oauth2Client.credentials;

  if (credentials.expiry_date && credentials.expiry_date < Date.now() + 60000) {
    console.log('[Google] Token expiring soon, refreshing...');
    const { credentials: newCredentials } = await oauth2Client.refreshAccessToken();

    db.prepare(`
      UPDATE google_tokens
      SET access_token = ?, expiry_date = ?, updated_at = datetime('now')
      WHERE id = 1
    `).run(newCredentials.access_token, newCredentials.expiry_date);
  }
}

/**
 * Create an event in Google Calendar
 * @param {Object} eventData - Event data (already privacy-filtered)
 * @returns {Object} Created event from Google
 */
async function createEvent(eventData) {
  if (!calendar) {
    throw new Error('Google Calendar not authenticated');
  }

  await refreshTokenIfNeeded();

  const response = await calendar.events.insert({
    calendarId: env.GOOGLE_CALENDAR_ID,
    resource: eventData,
  });

  console.log(`[Google] Created event: ${response.data.id}`);
  return response.data;
}

/**
 * Update an event in Google Calendar
 * @param {string} eventId - Google Calendar event ID
 * @param {Object} eventData - Updated event data
 * @returns {Object} Updated event from Google
 */
async function updateEvent(eventId, eventData) {
  if (!calendar) {
    throw new Error('Google Calendar not authenticated');
  }

  await refreshTokenIfNeeded();

  const response = await calendar.events.update({
    calendarId: env.GOOGLE_CALENDAR_ID,
    eventId: eventId,
    resource: eventData,
  });

  console.log(`[Google] Updated event: ${eventId}`);
  return response.data;
}

/**
 * Delete an event from Google Calendar
 * @param {string} eventId - Google Calendar event ID
 */
async function deleteEvent(eventId) {
  if (!calendar) {
    throw new Error('Google Calendar not authenticated');
  }

  await refreshTokenIfNeeded();

  await calendar.events.delete({
    calendarId: env.GOOGLE_CALENDAR_ID,
    eventId: eventId,
  });

  console.log(`[Google] Deleted event: ${eventId}`);
}

/**
 * Get an event from Google Calendar
 * @param {string} eventId - Google Calendar event ID
 * @returns {Object} Event data
 */
async function getEvent(eventId) {
  if (!calendar) {
    throw new Error('Google Calendar not authenticated');
  }

  await refreshTokenIfNeeded();

  const response = await calendar.events.get({
    calendarId: env.GOOGLE_CALENDAR_ID,
    eventId: eventId,
  });

  return response.data;
}

/**
 * List events from Google Calendar
 * @param {Object} options - Query options
 * @param {string} [options.timeMin] - Start of time range (ISO string)
 * @param {string} [options.timeMax] - End of time range (ISO string)
 * @param {number} [options.maxResults] - Maximum events to return
 * @returns {Array} List of events
 */
async function listEvents(options = {}) {
  if (!calendar) {
    throw new Error('Google Calendar not authenticated');
  }

  await refreshTokenIfNeeded();

  const response = await calendar.events.list({
    calendarId: env.GOOGLE_CALENDAR_ID,
    timeMin: options.timeMin || new Date().toISOString(),
    timeMax: options.timeMax,
    maxResults: options.maxResults || 100,
    singleEvents: true,
    orderBy: 'startTime',
  });

  return response.data.items || [];
}

/**
 * Set up push notifications (webhook) for calendar changes
 * @param {string} webhookUrl - URL to receive notifications
 * @returns {Object} Channel information
 */
async function setupPushNotifications(webhookUrl) {
  if (!calendar) {
    throw new Error('Google Calendar not authenticated');
  }

  await refreshTokenIfNeeded();

  const { v4: uuidv4 } = require('uuid');
  const channelId = uuidv4();

  // Channel expires in 7 days (Google's max)
  const expiration = Date.now() + 7 * 24 * 60 * 60 * 1000;

  const response = await calendar.events.watch({
    calendarId: env.GOOGLE_CALENDAR_ID,
    resource: {
      id: channelId,
      type: 'web_hook',
      address: webhookUrl,
      expiration: expiration.toString(),
    },
  });

  // Store channel info for later management
  db.prepare(`
    INSERT OR REPLACE INTO webhook_channels (id, resource_id, calendar_id, expiration, created_at)
    VALUES (?, ?, ?, ?, datetime('now'))
  `).run(channelId, response.data.resourceId, env.GOOGLE_CALENDAR_ID, expiration);

  console.log(`[Google] Push notifications set up, channel: ${channelId}`);
  return response.data;
}

/**
 * Stop push notifications for a channel
 * @param {string} channelId - Channel ID
 * @param {string} resourceId - Resource ID
 */
async function stopPushNotifications(channelId, resourceId) {
  if (!calendar) {
    throw new Error('Google Calendar not authenticated');
  }

  await calendar.channels.stop({
    resource: {
      id: channelId,
      resourceId: resourceId,
    },
  });

  db.prepare('DELETE FROM webhook_channels WHERE id = ?').run(channelId);
  console.log(`[Google] Stopped push notifications for channel: ${channelId}`);
}

// Initialize on module load
initializeFromStoredTokens();

module.exports = {
  getAuthUrl,
  exchangeCodeForTokens,
  isAuthenticated,
  createEvent,
  updateEvent,
  deleteEvent,
  getEvent,
  listEvents,
  setupPushNotifications,
  stopPushNotifications,
  initializeFromStoredTokens,
};
