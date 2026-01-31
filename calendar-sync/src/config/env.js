require('dotenv').config();

module.exports = {
  PORT: parseInt(process.env.PORT, 10) || 4200,
  NODE_ENV: process.env.NODE_ENV || 'development',

  // Google Calendar
  GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID || '',
  GOOGLE_CLIENT_SECRET: process.env.GOOGLE_CLIENT_SECRET || '',
  GOOGLE_REDIRECT_URI: process.env.GOOGLE_REDIRECT_URI || 'http://localhost:4200/api/auth/google/callback',
  GOOGLE_CALENDAR_ID: process.env.GOOGLE_CALENDAR_ID || 'primary',

  // AI Front Desk
  FRONTDESK_API_URL: process.env.FRONTDESK_API_URL || '',
  FRONTDESK_API_KEY: process.env.FRONTDESK_API_KEY || '',

  // Webhook
  WEBHOOK_SECRET: process.env.WEBHOOK_SECRET || '',

  // External Frontdesk
  EXTERNAL_FRONTDESK_URL: process.env.EXTERNAL_FRONTDESK_URL || '',
  EXTERNAL_FRONTDESK_API_KEY: process.env.EXTERNAL_FRONTDESK_API_KEY || '',
};
