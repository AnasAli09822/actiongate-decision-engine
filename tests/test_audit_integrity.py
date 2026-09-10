from __future__ import annotations

import sqlite3

import pytest

import app.audit as audit


def test_audit_table_rejects_update_and_delete(tmp_path, monkeypatch):
    db_path = tmp_path / "audit.db"
    monkeypatch.setattr(audit, "DB_PATH", db_path)
    audit.init_db()
    audit.append_event("dec_test", "input_received", {"hello": "world"})

    conn = sqlite3.connect(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE audit_events SET stage = 'tampered' WHERE decision_id = ?", ("dec_test",))
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM audit_events WHERE decision_id = ?", ("dec_test",))
    finally:
        conn.close()


def test_hash_chain_detects_direct_file_level_tampering(tmp_path, monkeypatch):
    db_path = tmp_path / "audit.db"
    monkeypatch.setattr(audit, "DB_PATH", db_path)
    audit.init_db()
    audit.append_event("dec_test", "input_received", {"hello": "world"})
    audit.append_event("dec_test", "decision_emitted", {"decision": "execute"})

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DROP TRIGGER audit_events_no_update")
        conn.execute("UPDATE audit_events SET payload_json = '{\"hello\":\"tampered\"}' WHERE decision_id = 'dec_test' AND sequence = 1")
        conn.commit()
    finally:
        conn.close()

    trail = audit.get_audit("dec_test")
    assert trail is not None
    assert trail["chain_valid"] is False
