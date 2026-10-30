"""Local append-only employee review and paid-request budget ledger."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from leakprobe.paths import OUTPUTS
from leakprobe.ui.runtime_settings import review_database

DEFAULT_PATH = OUTPUTS / "operations" / "alerts.sqlite3"
STATUSES = ("Acknowledged", "Under review", "Leak confirmed", "No leak",
            "Further investigation required")


class AlertStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else review_database()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS alerts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, alert_id TEXT NOT NULL, "
                       "at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def register(self, alert):
        with self.connect() as db:
            inserted = db.execute("INSERT OR IGNORE INTO alerts VALUES (?, ?)",
                                  (alert["alert_id"], json.dumps(alert, allow_nan=False)))
            if inserted.rowcount:
                self._event(db, alert["alert_id"], "detected", {"prediction": alert["prediction"]})

    def review(self, alert_id, status, reviewer, notes=""):
        if status not in STATUSES or not reviewer.strip() or len(notes) > 4000 or len(reviewer) > 120:
            raise ValueError("Provide a reviewer, a valid status, and notes of at most 4,000 characters.")
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM alerts WHERE id=?", (alert_id,)).fetchone():
                raise ValueError("Unknown alert.")
            self._event(db, alert_id, "review", {"status": status, "reviewer": reviewer.strip(), "notes": notes})

    def _event(self, db, alert_id, kind, payload):
        db.execute("INSERT INTO events(alert_id,at,kind,payload) VALUES(?,?,?,?)",
                   (alert_id, datetime.now(timezone.utc).isoformat(), kind, json.dumps(payload)))

    def reserve_ai(self, alert_id, limit=2):
        # Transaction protects concurrent tabs and retains failed-attempt accounting.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM alerts WHERE id=?", (alert_id,)).fetchone():
                raise ValueError("Unknown alert.")
            count = db.execute("SELECT count(*) FROM events WHERE alert_id=? AND kind='ai_request'", (alert_id,)).fetchone()[0]
            pending = db.execute("SELECT count(*) FROM events WHERE alert_id=? AND kind='ai_request' "
                                 "AND id NOT IN (SELECT CAST(json_extract(payload,'$.request_id') AS INTEGER) "
                                 "FROM events WHERE alert_id=? AND kind='ai_result')", (alert_id, alert_id)).fetchone()[0]
            if count >= limit or pending:
                raise ValueError("AI request budget exhausted or an investigation is already running.")
            self._event(db, alert_id, "ai_request", {"attempt": count + 1})
            return db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def finish_ai(self, alert_id, request_id, status, trace_file=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM events WHERE id=? AND alert_id=? AND kind='ai_request'",
                              (request_id, alert_id)).fetchone():
                raise ValueError("Unknown AI request.")
            if any(event.get("request_id") == request_id for event in self.events(alert_id)
                   if event["kind"] == "ai_result"):
                raise ValueError("AI request already has a result.")
            self._event(db, alert_id, "ai_result", {"request_id": request_id, "status": status, "trace_file": trace_file})

    def events(self, alert_id):
        with self.connect() as db:
            return [{"event_id": row[0], "at": row[1], "kind": row[2], **json.loads(row[3])}
                    for row in db.execute("SELECT id,at,kind,payload FROM events WHERE alert_id=? ORDER BY id", (alert_id,))]

    def alerts(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM alerts ORDER BY rowid DESC")]
