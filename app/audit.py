from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("ACTIONGATE_DB", "data/actiongate.db"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                stage TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                UNIQUE(decision_id, sequence)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_decision_id ON audit_events(decision_id)"
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS audit_events_no_update
            BEFORE UPDATE ON audit_events
            BEGIN
                SELECT RAISE(ABORT, 'audit_events is append-only');
            END;
            """
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
            BEFORE DELETE ON audit_events
            BEGIN
                SELECT RAISE(ABORT, 'audit_events is append-only');
            END;
            """
        )


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _event_hash(
    decision_id: str,
    sequence: int,
    stage: str,
    payload_json: str,
    created_at: str,
    previous_hash: str,
) -> str:
    raw = "|".join(
        [decision_id, str(sequence), stage, payload_json, created_at, previous_hash]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_event(decision_id: str, stage: str, payload: dict[str, Any]) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    payload_json = _canonical_json(payload)

    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT sequence, event_hash
            FROM audit_events
            WHERE decision_id = ?
            ORDER BY sequence DESC
            LIMIT 1
            """,
            (decision_id,),
        ).fetchone()

        sequence = 1 if row is None else int(row["sequence"]) + 1
        previous_hash = "GENESIS" if row is None else str(row["event_hash"])
        event_hash = _event_hash(
            decision_id, sequence, stage, payload_json, created_at, previous_hash
        )

        conn.execute(
            """
            INSERT INTO audit_events
            (decision_id, sequence, stage, payload_json, created_at, previous_hash, event_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                sequence,
                stage,
                payload_json,
                created_at,
                previous_hash,
                event_hash,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "sequence": sequence,
        "stage": stage,
        "payload": payload,
        "created_at": created_at,
        "previous_hash": previous_hash,
        "event_hash": event_hash,
    }


def get_audit(decision_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT sequence, stage, payload_json, created_at, previous_hash, event_hash
            FROM audit_events
            WHERE decision_id = ?
            ORDER BY sequence ASC
            """,
            (decision_id,),
        ).fetchall()

    if not rows:
        return None

    events: list[dict[str, Any]] = []
    expected_previous = "GENESIS"
    chain_valid = True

    for row in rows:
        payload_json = str(row["payload_json"])
        recalculated = _event_hash(
            decision_id,
            int(row["sequence"]),
            str(row["stage"]),
            payload_json,
            str(row["created_at"]),
            str(row["previous_hash"]),
        )
        if str(row["previous_hash"]) != expected_previous or recalculated != str(row["event_hash"]):
            chain_valid = False

        expected_previous = str(row["event_hash"])
        events.append(
            {
                "sequence": int(row["sequence"]),
                "stage": str(row["stage"]),
                "payload": json.loads(payload_json),
                "created_at": str(row["created_at"]),
                "previous_hash": str(row["previous_hash"]),
                "event_hash": str(row["event_hash"]),
            }
        )

    return {"decision_id": decision_id, "chain_valid": chain_valid, "events": events}
