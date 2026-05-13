-- 001_init.sql — SQLite-friendly schema

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  visibility TEXT NOT NULL,
  language TEXT NOT NULL,
  created_at TEXT NOT NULL,
  text TEXT NOT NULL,
  edge_case TEXT,
  metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS risk_scores (
  id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL,
  computed_at TEXT NOT NULL,
  total_score REAL NOT NULL,
  bucket TEXT NOT NULL,
  reasons_json TEXT NOT NULL,
  decomposition_json TEXT NOT NULL,
  FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trend_topics (
  term TEXT PRIMARY KEY,
  volume INTEGER NOT NULL,
  tone REAL NOT NULL,
  last_seen TEXT NOT NULL,
  source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  item_id TEXT NOT NULL,
  trend_term TEXT NOT NULL,
  old_bucket TEXT,
  new_bucket TEXT,
  risk_delta REAL,
  details_json TEXT NOT NULL,
  FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
  FOREIGN KEY (trend_term) REFERENCES trend_topics(term) ON DELETE CASCADE
);
