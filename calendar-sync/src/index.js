const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const env = require('./config/env');

// Initialize database (creates tables if needed)
require('./models/database');

// Import routes
const authRoutes = require('./routes/auth');
const syncRoutes = require('./routes/sync');
const webhookRoutes = require('./routes/webhooks');

const app = express();

// Security middleware
app.use(helmet());
app.use(cors({
  origin: env.NODE_ENV === 'production'
    ? ['https://agent.opentruthai.com', 'https://calendar.google.com']
    : '*',
}));

// Body parsing
app.use(express.json());

// Request logging
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// Health check
app.get('/health', (req, res) => {
  const googleCalendar = require('./services/googleCalendar');
  res.json({
    status: 'ok',
    uptime: process.uptime(),
    googleConnected: googleCalendar.isAuthenticated(),
  });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/sync', syncRoutes);
app.use('/api/webhook', webhookRoutes);

// Dashboard (simple status page)
app.get('/', (req, res) => {
  const googleCalendar = require('./services/googleCalendar');
  const syncEngine = require('./services/syncEngine');
  const stats = syncEngine.getStats();

  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Calendar Sync Hub</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          max-width: 800px;
          margin: 0 auto;
          padding: 40px 20px;
          background: #0e0e20;
          color: #e0e0e0;
        }
        h1 { color: #d4af37; }
        .status {
          padding: 20px;
          border-radius: 8px;
          margin: 20px 0;
          background: #1a1a2e;
        }
        .connected { border-left: 4px solid #22c55e; }
        .disconnected { border-left: 4px solid #ef4444; }
        a {
          color: #3b82f6;
          text-decoration: none;
        }
        a:hover { text-decoration: underline; }
        .stat {
          display: inline-block;
          padding: 10px 20px;
          margin: 5px;
          background: #2a2a4a;
          border-radius: 6px;
        }
        .stat-value {
          font-size: 24px;
          font-weight: bold;
          color: #d4af37;
        }
        .stat-label {
          font-size: 12px;
          color: #888;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 20px;
        }
        th, td {
          padding: 10px;
          text-align: left;
          border-bottom: 1px solid #2a2a4a;
        }
        th { color: #888; font-weight: 600; }
      </style>
    </head>
    <body>
      <h1>Calendar Sync Hub</h1>
      <p>Bidirectional sync between Front Desk and Google Calendar</p>

      <div class="status ${stats.googleConnected ? 'connected' : 'disconnected'}">
        <h3>Google Calendar</h3>
        <p>Status: <strong>${stats.googleConnected ? 'Connected' : 'Not Connected'}</strong></p>
        ${!stats.googleConnected ? '<p><a href="/api/auth/google">Connect Google Calendar &rarr;</a></p>' : ''}
      </div>

      <h2>Sync Statistics</h2>
      <div>
        <div class="stat">
          <div class="stat-value">${stats.totalMappings}</div>
          <div class="stat-label">Total Mappings</div>
        </div>
        <div class="stat">
          <div class="stat-value">${stats.synced}</div>
          <div class="stat-label">Synced</div>
        </div>
        <div class="stat">
          <div class="stat-value">${stats.errors}</div>
          <div class="stat-label">Errors</div>
        </div>
      </div>

      <h2>Recent Activity</h2>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Action</th>
            <th>Source</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${stats.recentActivity.map(log => `
            <tr>
              <td>${log.created_at}</td>
              <td>${log.action}</td>
              <td>${log.source}</td>
              <td>${log.success ? '✓' : '✗ ' + (log.error_message || '')}</td>
            </tr>
          `).join('')}
          ${stats.recentActivity.length === 0 ? '<tr><td colspan="4">No recent activity</td></tr>' : ''}
        </tbody>
      </table>

      <h2>API Endpoints</h2>
      <ul>
        <li><code>GET /health</code> - Health check</li>
        <li><code>GET /api/auth/google</code> - Connect Google Calendar</li>
        <li><code>GET /api/auth/status</code> - Auth status</li>
        <li><code>POST /api/sync/event</code> - Sync event to Google</li>
        <li><code>POST /api/sync/full</code> - Full bidirectional sync</li>
        <li><code>GET /api/sync/status</code> - Sync stats</li>
        <li><code>POST /api/webhook/frontdesk</code> - Front Desk notifications</li>
        <li><code>POST /api/webhook/google</code> - Google notifications</li>
      </ul>

      <h2>Privacy Filter</h2>
      <p>Events synced to Google Calendar only show: <strong>FirstName + Last 2 digits of phone</strong></p>
      <p>Example: "David Scott (555) 123-4567" → <strong>"David 67"</strong></p>
    </body>
    </html>
  `);
});

// Error handling
app.use((err, req, res, next) => {
  console.error(`[Error] ${err.message}`, err.stack);
  res.status(err.status || 500).json({
    error: env.NODE_ENV === 'production' ? 'Internal server error' : err.message,
  });
});

// Start server
app.listen(env.PORT, () => {
  console.log(`[Server] Calendar Sync Hub running on port ${env.PORT} (${env.NODE_ENV})`);
  console.log(`[Server] Dashboard: http://localhost:${env.PORT}`);

  // Check Google connection status
  const googleCalendar = require('./services/googleCalendar');
  if (googleCalendar.isAuthenticated()) {
    console.log('[Server] Google Calendar: Connected');
  } else {
    console.log('[Server] Google Calendar: Not connected');
    console.log(`[Server] Connect at: http://localhost:${env.PORT}/api/auth/google`);
  }
});
