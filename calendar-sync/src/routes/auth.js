const { Router } = require('express');
const googleCalendar = require('../services/googleCalendar');

const router = Router();

/**
 * GET /api/auth/google
 * Redirect to Google OAuth consent screen
 */
router.get('/google', (req, res) => {
  const authUrl = googleCalendar.getAuthUrl();
  res.redirect(authUrl);
});

/**
 * GET /api/auth/google/callback
 * Handle OAuth callback from Google
 */
router.get('/google/callback', async (req, res) => {
  const { code, error } = req.query;

  if (error) {
    console.error('[Auth] Google OAuth error:', error);
    return res.status(400).send(`
      <html>
        <body style="font-family: sans-serif; padding: 40px; text-align: center;">
          <h1>Authorization Failed</h1>
          <p>Error: ${error}</p>
          <a href="/api/auth/google">Try Again</a>
        </body>
      </html>
    `);
  }

  if (!code) {
    return res.status(400).send('Missing authorization code');
  }

  try {
    await googleCalendar.exchangeCodeForTokens(code);

    res.send(`
      <html>
        <body style="font-family: sans-serif; padding: 40px; text-align: center;">
          <h1>Google Calendar Connected!</h1>
          <p>You can now close this window.</p>
          <p>The calendar sync is now active.</p>
          <script>
            setTimeout(() => window.close(), 3000);
          </script>
        </body>
      </html>
    `);
  } catch (err) {
    console.error('[Auth] Failed to exchange code:', err.message);
    res.status(500).send(`
      <html>
        <body style="font-family: sans-serif; padding: 40px; text-align: center;">
          <h1>Connection Failed</h1>
          <p>Error: ${err.message}</p>
          <a href="/api/auth/google">Try Again</a>
        </body>
      </html>
    `);
  }
});

/**
 * GET /api/auth/status
 * Check authentication status
 */
router.get('/status', (req, res) => {
  res.json({
    google: {
      connected: googleCalendar.isAuthenticated(),
    },
  });
});

module.exports = router;
