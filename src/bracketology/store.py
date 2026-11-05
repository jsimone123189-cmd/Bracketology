from __future__ import annotations
"""Daily timestamped snapshots with source metadata, in SQLite (mirrors to Cloudflare D1 later; same schema)."""
import json, sqlite3, time
SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY, source TEXT, season INT, taken_at TEXT, asof TEXT,
  url TEXT, n_rows INT, ok INT, notes TEXT);
CREATE TABLE IF NOT EXISTS snapshot_rows(snapshot_id INT, team_key TEXT, data TEXT);
CREATE INDEX IF NOT EXISTS ix_rows ON snapshot_rows(snapshot_id, team_key);
"""
def connect(path="data/bracketology.sqlite"):
    c = sqlite3.connect(path); c.executescript(SCHEMA); return c

def save(c, payload: dict, season: int, ok: bool = True, notes: str = "") -> int:
    cur = c.execute("INSERT INTO snapshots(source,season,taken_at,asof,url,n_rows,ok,notes) VALUES(?,?,?,?,?,?,?,?)",
        (payload["source"], season, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), payload.get("asof"),
         payload.get("url"), len(payload["rows"]), int(ok), notes))
    sid = cur.lastrowid
    c.executemany("INSERT INTO snapshot_rows VALUES(?,?,?)",
                  [(sid, r.get("team_key", r.get("team")), json.dumps(r)) for r in payload["rows"]])
    c.commit(); return sid
