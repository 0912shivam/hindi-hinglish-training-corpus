from __future__ import annotations

from pathlib import Path
import sqlite3


class ExactDeduper:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._pending = 0
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exact_dedup (
                normalized_hash TEXT PRIMARY KEY,
                canonical_doc_id TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def check_or_add(self, normalized_hash: str, doc_id: str) -> tuple[bool, str]:
        cur = self.conn.execute(
            "SELECT canonical_doc_id FROM exact_dedup WHERE normalized_hash = ?",
            (normalized_hash,),
        )
        row = cur.fetchone()
        if row:
            return False, str(row[0])

        self.conn.execute(
            "INSERT INTO exact_dedup (normalized_hash, canonical_doc_id) VALUES (?, ?)",
            (normalized_hash, doc_id),
        )
        self._pending += 1
        if self._pending >= 2000:
            self.conn.commit()
            self._pending = 0
        return True, doc_id

    def close(self) -> None:
        if self._pending:
            self.conn.commit()
            self._pending = 0
        self.conn.close()
