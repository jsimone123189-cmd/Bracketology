-- Private review store. Edits and freezes are append-only: UPDATE and DELETE abort (an undo is a new row).
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
