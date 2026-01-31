const Database = require('better-sqlite3');
const path = require('path');

const dbPath = path.join(__dirname, '../../data/sync.db');
const db = new Database(dbPath);

// Enable foreign keys and WAL mode for better performance
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

// Initialize tables
db.exec(`
  -- Event mappings between different calendar systems
  CREATE TABLE IF NOT EXISTS event_mappings (
    id TEXT PRIMARY KEY,
    frontdesk_event_id TEXT,
    google_event_id TEXT,
    external_event_id TEXT,

    -- Store the privacy-filtered title sent to Google
    google_title TEXT,

    -- Original data (for reverse lookups)
    original_customer_name TEXT,
    original_phone_last_two TEXT,

    -- Timestamps
    event_start TEXT,
    event_end TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),

    -- Sync status
    sync_status TEXT DEFAULT 'synced',
    last_sync_error TEXT,
    last_synced_at TEXT
  );

  -- Google OAuth tokens
  CREATE TABLE IF NOT EXISTS google_tokens (
    id INTEGER PRIMARY KEY DEFAULT 1,
    access_token TEXT,
    refresh_token TEXT,
    expiry_date INTEGER,
    scope TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
  );

  -- Sync log for debugging
  CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    source TEXT NOT NULL,
    event_id TEXT,
    details TEXT,
    success INTEGER DEFAULT 1,
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Google Calendar webhook channel
  CREATE TABLE IF NOT EXISTS webhook_channels (
    id TEXT PRIMARY KEY,
    resource_id TEXT,
    calendar_id TEXT,
    expiration INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
  );

  -- Indexes for fast lookups
  CREATE INDEX IF NOT EXISTS idx_frontdesk_id ON event_mappings(frontdesk_event_id);
  CREATE INDEX IF NOT EXISTS idx_google_id ON event_mappings(google_event_id);
  CREATE INDEX IF NOT EXISTS idx_external_id ON event_mappings(external_event_id);
  CREATE INDEX IF NOT EXISTS idx_sync_status ON event_mappings(sync_status);
`);

module.exports = db;
