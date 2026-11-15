-- Backup database: a second, append-only copy of every record, filled daily and after each freeze/publication by the Worker.
-- Nothing here can be updated or deleted, so it keeps the whole season (D1 Free: 500 MB per database; a season is about 40 MB).

CREATE TABLE reviews (
  season INTEGER NOT NULL,
  collected_at TEXT NOT NULL,            -- when the data were collected (from the build)
  generated_at TEXT NOT NULL,
  uploaded_at TEXT NOT NULL,             -- server time
  body TEXT NOT NULL,                    -- review JSON (B1, B2, evidence); never contains edits
  body_sha256 TEXT NOT NULL,
  core TEXT NOT NULL,                    -- just what freezes and B3 need (brackets, order, team info, inputs, checks): small, so it fits the free CPU limit
  PRIMARY KEY (season, collected_at)
);
CREATE TRIGGER reviews_no_update BEFORE UPDATE ON reviews BEGIN SELECT RAISE(ABORT, 'reviews are immutable'); END;
CREATE TRIGGER reviews_no_delete BEFORE DELETE ON reviews BEGIN SELECT RAISE(ABORT, 'reviews are immutable'); END;

CREATE TABLE edits (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  season INTEGER NOT NULL,
  id TEXT NOT NULL UNIQUE,               -- server-generated
  at TEXT NOT NULL,                      -- server time; the phone's clock is kept only as client_at
  client_at TEXT,
  body TEXT NOT NULL                     -- the edit as applied by the engine (op, team, line, reason, confidence, explanation, undo_of)
);
CREATE INDEX edits_season ON edits (season, seq);
CREATE TRIGGER edits_no_update BEFORE UPDATE ON edits BEGIN SELECT RAISE(ABORT, 'edits are append-only'); END;
CREATE TRIGGER edits_no_delete BEFORE DELETE ON edits BEGIN SELECT RAISE(ABORT, 'edits are append-only'); END;

CREATE TABLE freezes (
  season INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('research', 'final')),
  frozen_at TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  body TEXT NOT NULL,                    -- exact bytes that were hashed
  PRIMARY KEY (season, kind)             -- one of each, ever
);
CREATE TRIGGER freezes_no_update BEFORE UPDATE ON freezes BEGIN SELECT RAISE(ABORT, 'freezes are immutable'); END;
CREATE TRIGGER freezes_no_delete BEFORE DELETE ON freezes BEGIN SELECT RAISE(ABORT, 'freezes are immutable'); END;

CREATE TABLE verifications (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  season INTEGER NOT NULL,
  kind TEXT NOT NULL,
  checked_at TEXT NOT NULL,
  ok INTEGER NOT NULL,
  body TEXT NOT NULL
);

-- What the public site may show: a B3 you chose to publish (lines only). Drafts never leave the Worker.
CREATE TABLE publications (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  season INTEGER NOT NULL,
  at TEXT NOT NULL,                      -- server time
  review_collected_at TEXT NOT NULL,
  edits_through_seq INTEGER NOT NULL,    -- every edit up to this one is included
  lines TEXT NOT NULL,                   -- [{key, team, line}]
  sha256 TEXT NOT NULL
);
CREATE TRIGGER publications_no_update BEFORE UPDATE ON publications BEGIN SELECT RAISE(ABORT, 'publications are append-only'); END;
CREATE TRIGGER publications_no_delete BEFORE DELETE ON publications BEGIN SELECT RAISE(ABORT, 'publications are append-only'); END;

CREATE TRIGGER verifications_no_update BEFORE UPDATE ON verifications BEGIN SELECT RAISE(ABORT, 'backup is append-only'); END;
CREATE TRIGGER verifications_no_delete BEFORE DELETE ON verifications BEGIN SELECT RAISE(ABORT, 'backup is append-only'); END;

CREATE TABLE backup_runs (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  ok INTEGER NOT NULL,
  copied TEXT NOT NULL,                  -- rows copied per table this run
  counts TEXT NOT NULL,                  -- rows per table, main vs backup, after the run
  digest TEXT NOT NULL                   -- SHA-256 over the full edit log (seq|id|at|client_at|body), equal in both
);
CREATE TRIGGER backup_runs_no_update BEFORE UPDATE ON backup_runs BEGIN SELECT RAISE(ABORT, 'backup is append-only'); END;
CREATE TRIGGER backup_runs_no_delete BEFORE DELETE ON backup_runs BEGIN SELECT RAISE(ABORT, 'backup is append-only'); END;
