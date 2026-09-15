"""Transactional cursor/record checkpoints; request attempts survive interruptions."""
import json
import sqlite3
from datetime import datetime, timezone
from pharos.backends.openalex_api import observe


def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS works (id TEXT PRIMARY KEY, raw TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (time TEXT NOT NULL, event TEXT NOT NULL);
        """)

    def get(self, key, default=None):
        row = self.db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.db:
            self._set(key, value)

    def _set(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO state VALUES (?,?)", (key, json.dumps(value)))

    def audit(self, event):
        with self.db:
            self.db.execute("INSERT INTO events VALUES (?,?)", (now(), json.dumps(event)))

    def count(self):
        return self.db.execute("SELECT count(*) FROM works").fetchone()[0]

    def page(self, result, previous_cursor):
        next_cursor = result["meta"]["next_cursor"]
        if next_cursor is not None and (not isinstance(next_cursor, str) or next_cursor == previous_cursor):
            raise ValueError("Invalid or repeated cursor; retrieval stopped.")
        rows = [(observe(raw).id, json.dumps(raw)) for raw in result["results"]]
        if not rows and next_cursor is not None:
            raise ValueError("Empty page has a continuation cursor; retrieval stopped.")
        with self.db:
            inserted = 0
            for row in rows:
                inserted += self.db.execute("INSERT OR IGNORE INTO works VALUES (?,?)", row).rowcount
            self._set("duplicate_records", self.get("duplicate_records", 0) + len(rows) - inserted)
            self._set("cursor", next_cursor)
            self._set("complete", next_cursor is None)
            self._set("last_page_at", now())
            self._set("last_api_count", result["meta"].get("count"))

    def observations(self):
        return [observe(json.loads(row[0])) for row in self.db.execute("SELECT raw FROM works ORDER BY id")]

    def receipt(self, status, warning=None):
        events = [json.loads(r[0]) for r in self.db.execute("SELECT event FROM events")]
        attempts = sum(e["event"] == "attempt" for e in events)
        responses = [e for e in events if e["event"] == "response"]
        costs = [e["reported_cost_usd"] for e in responses if e["reported_cost_usd"] is not None]
        estimate = self.get("estimate", {})
        warnings = ["Requests interrupted before a response may still be billed; reported cost is not an account total."]
        if warning: warnings.append(warning)
        if self.get("duplicate_records", 0): warnings.append("Duplicate work IDs across pages were counted once; first observed assertions retained.")
        if status == "complete" and self.count() != estimate.get("estimated_records"):
            warnings.append("Retrieved unique records differ from the initial API count; inspect live-data drift before using the profile.")
        return {"schema_version": "1.0", "backend": "openalex_api", "source_date": None,
            "started_at": self.get("started_at"), "ended_at": now(), "retrieved_at": self.get("last_page_at"),
            "completion_state": status, "records": self.count(), "calls": attempts,
            "successful_responses": len(responses), "download_bytes": sum(e["bytes"] for e in responses),
            "reported_cost_usd": round(sum(costs), 8) if costs else None,
            "responses_with_reported_cost": len(costs), "estimated_api_cost_usd": estimate.get("estimated_api_cost_usd"),
            "estimated_records": estimate.get("estimated_records"), "record_count_difference": self.count() - estimate.get("estimated_records", 0),
            "duplicate_records": self.get("duplicate_records", 0), "query": self.get("query"),
            "corpus_specification_hash": self.get("hash"), "warnings": warnings}

    def close(self):
        self.db.close()
