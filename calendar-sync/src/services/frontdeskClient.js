const axios = require('axios');
const env = require('../config/env');

/**
 * Front Desk API Client
 *
 * Communicates with the main calendar at agent.opentruthai.com
 */

const client = axios.create({
  baseURL: env.FRONTDESK_API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    ...(env.FRONTDESK_API_KEY && { Authorization: `Bearer ${env.FRONTDESK_API_KEY}` }),
  },
});

/**
 * Get events from Front Desk calendar
 * @param {Object} options - Query options
 * @param {string} [options.startDate] - Start of date range (ISO string)
 * @param {string} [options.endDate] - End of date range (ISO string)
 * @returns {Array} List of appointments
 */
async function getEvents(options = {}) {
  try {
    const response = await client.get('/calendar/events', {
      params: {
        startDate: options.startDate,
        endDate: options.endDate,
      },
    });
    return response.data.events || response.data || [];
  } catch (error) {
    console.error('[FrontDesk] Failed to get events:', error.message);
    throw error;
  }
}

/**
 * Create an event in Front Desk calendar
 * @param {Object} event - Event data
 * @returns {Object} Created event
 */
async function createEvent(event) {
  try {
    const response = await client.post('/calendar/events', event);
    console.log(`[FrontDesk] Created event: ${response.data.id}`);
    return response.data;
  } catch (error) {
    console.error('[FrontDesk] Failed to create event:', error.message);
    throw error;
  }
}

/**
 * Update an event in Front Desk calendar
 * @param {string} eventId - Event ID
 * @param {Object} updates - Updated fields
 * @returns {Object} Updated event
 */
async function updateEvent(eventId, updates) {
  try {
    const response = await client.put(`/calendar/events/${eventId}`, updates);
    console.log(`[FrontDesk] Updated event: ${eventId}`);
    return response.data;
  } catch (error) {
    console.error('[FrontDesk] Failed to update event:', error.message);
    throw error;
  }
}

/**
 * Delete an event from Front Desk calendar
 * @param {string} eventId - Event ID
 */
async function deleteEvent(eventId) {
  try {
    await client.delete(`/calendar/events/${eventId}`);
    console.log(`[FrontDesk] Deleted event: ${eventId}`);
  } catch (error) {
    console.error('[FrontDesk] Failed to delete event:', error.message);
    throw error;
  }
}

/**
 * Get a single event by ID
 * @param {string} eventId - Event ID
 * @returns {Object} Event data
 */
async function getEvent(eventId) {
  try {
    const response = await client.get(`/calendar/events/${eventId}`);
    return response.data;
  } catch (error) {
    console.error('[FrontDesk] Failed to get event:', error.message);
    throw error;
  }
}

/**
 * Register a webhook for event changes
 * @param {string} webhookUrl - URL to receive notifications
 * @returns {Object} Webhook registration response
 */
async function registerWebhook(webhookUrl) {
  try {
    const response = await client.post('/calendar/webhook', {
      url: webhookUrl,
      events: ['event.created', 'event.updated', 'event.deleted'],
    });
    console.log('[FrontDesk] Webhook registered');
    return response.data;
  } catch (error) {
    console.error('[FrontDesk] Failed to register webhook:', error.message);
    throw error;
  }
}

/**
 * Create a call log entry in Front Desk
 * @param {Object} callData - Call log data
 * @returns {Object} Created call log
 */
async function createCallLog(callData) {
  try {
    const response = await client.post('/api/call-webhook/', {
      caller_name: callData.customerName,
      caller_number: callData.customerPhone,
      direction: callData.direction || 'inbound',
      duration: callData.duration || 0,
      transcript: callData.transcript || '',
      category: callData.category || '',
      call_id: callData.callId || callData.id,
      // Detection fields
      action_detected: callData.action ? callData.action.toUpperCase() : '',
      metal_detected: callData.metal ? callData.metal.toUpperCase() : '',
      quantity_detected: callData.quantity || null,
      form_detected: callData.form ? callData.form.toUpperCase() : '',
    });
    console.log(`[FrontDesk] Created call log: ${response.data.id}`);
    return response.data;
  } catch (error) {
    console.error('[FrontDesk] Failed to create call log:', error.message);
    // Don't throw - call log creation is optional
    return { error: error.message };
  }
}

module.exports = {
  getEvents,
  createEvent,
  updateEvent,
  deleteEvent,
  getEvent,
  registerWebhook,
  createCallLog,
};
