const { Router } = require('express');
const crypto = require('crypto');
const env = require('../config/env');
const syncEngine = require('../services/syncEngine');
const googleCalendar = require('../services/googleCalendar');

const router = Router();

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
      eventData = {
        id: body.call_id || body.id || `ext-${Date.now()}`,
        customerName: body.caller_name || body.name || body.customer_name || 'Customer',
        customerPhone: body.caller_number || body.phone || body.customer_phone || '',
        startTime: body.appointment_time || body.scheduled_time || body.start_time || body.datetime,
        endTime: body.end_time || body.appointment_end,
        purpose: body.reason || body.purpose || body.service || body.call_summary || 'Appointment',
        notes: body.notes || body.transcript || body.call_notes || '',
      };
    } else {
      // Flat format - try to extract what we can
      eventData = {
        id: body.id || body.appointmentId || body.appointment_id || `ext-${Date.now()}`,
        customerName: body.customerName || body.customer_name || body.name || body.caller || 'Customer',
        customerPhone: body.customerPhone || body.customer_phone || body.phone || body.caller_number || '',
        startTime: body.startTime || body.start_time || body.datetime || body.appointment_time || body.start,
        endTime: body.endTime || body.end_time || body.end,
        purpose: body.purpose || body.service || body.reason || body.type || 'Appointment',
        notes: body.notes || '',
      };
    }

    console.log(`[Webhook] External parsed: type=${eventType}, name=${eventData.customerName}, phone=${eventData.customerPhone}`);

    // Map external event to our format with source marker
    const mappedEvent = {
      ...eventData,
      source: 'external',
    };

    if (!googleCalendar.isAuthenticated()) {
      console.warn('[Webhook] Google Calendar not connected');
      return res.json({ received: true, synced: false, reason: 'google_not_connected' });
    }

    let result;

    if (eventType.includes('cancel') || eventType.includes('delet')) {
      result = await syncEngine.syncDelete('frontdesk', mappedEvent.id);
    } else {
      // Created or updated
      result = await syncEngine.syncFrontdeskToGoogle(mappedEvent);
    }

    console.log(`[Webhook] External sync result:`, result);
    res.json({ received: true, synced: true, result });
  } catch (err) {
    console.error('[Webhook] External error:', err.message);
    res.json({ received: true, synced: false, error: err.message });
  }
});

module.exports = router;
