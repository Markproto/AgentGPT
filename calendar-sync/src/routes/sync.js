const { Router } = require('express');
const syncEngine = require('../services/syncEngine');
const googleCalendar = require('../services/googleCalendar');

const router = Router();

/**
 * POST /api/sync/event
 * Sync a single event from Front Desk to Google Calendar
 *
 * Body: { event: { id, customerName, customerPhone, startTime, endTime, ... } }
 */
router.post('/event', async (req, res, next) => {
  try {
    const { event } = req.body;

    if (!event) {
      return res.status(400).json({ error: 'Missing event data' });
    }

    if (!googleCalendar.isAuthenticated()) {
      return res.status(503).json({
        error: 'Google Calendar not connected',
        authUrl: '/api/auth/google',
      });
    }

    const result = await syncEngine.syncFrontdeskToGoogle(event);
    res.json(result);
  } catch (err) {
    next(err);
  }
});

/**
 * PUT /api/sync/event/:id
 * Update a synced event
 *
 * Body: { event: { ... updated fields ... } }
 */
router.put('/event/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { event } = req.body;

    if (!event) {
      return res.status(400).json({ error: 'Missing event data' });
    }

    // Add ID to event for lookup
    event.id = id;

    const result = await syncEngine.syncFrontdeskToGoogle(event);
    res.json(result);
  } catch (err) {
    next(err);
  }
});

/**
 * DELETE /api/sync/event/:id
 * Delete a synced event from all calendars
 *
 * Query: ?source=frontdesk|google (which calendar initiated delete)
 */
router.delete('/event/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const source = req.query.source || 'frontdesk';

    const result = await syncEngine.syncDelete(source, id);
    res.json(result);
  } catch (err) {
    next(err);
  }
});

/**
 * GET /api/sync/mappings
 * Get all event mappings
 */
router.get('/mappings', (req, res) => {
  const mappings = syncEngine.getAllMappings();
  res.json({ mappings });
});

/**
 * GET /api/sync/mapping/:id
 * Get mapping by Front Desk or Google event ID
 *
 * Query: ?source=frontdesk|google
 */
router.get('/mapping/:id', (req, res) => {
  const { id } = req.params;
  const source = req.query.source || 'frontdesk';

  const mapping = syncEngine.getMapping(source, id);

  if (!mapping) {
    return res.status(404).json({ error: 'Mapping not found' });
  }

  res.json(mapping);
});

/**
 * POST /api/sync/full
 * Trigger a full sync between all calendars
 *
 * Body: { startDate?, endDate? }
 */
router.post('/full', async (req, res, next) => {
  try {
    if (!googleCalendar.isAuthenticated()) {
      return res.status(503).json({
        error: 'Google Calendar not connected',
        authUrl: '/api/auth/google',
      });
    }

    const { startDate, endDate } = req.body;
    const results = await syncEngine.fullSync({ startDate, endDate });
    res.json(results);
  } catch (err) {
    next(err);
  }
});

/**
 * GET /api/sync/status
 * Get sync status and statistics
 */
router.get('/status', (req, res) => {
  const stats = syncEngine.getStats();
  res.json(stats);
});

module.exports = router;
