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

module.exports = {
  getEvents,
  createEvent,
  updateEvent,
  deleteEvent,
  getEvent,
  registerWebhook,
};
