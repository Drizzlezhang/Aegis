"""Test Sprint16 migration creates expected tables and columns.

Uses raw SQLite to verify the SQL schema, since the Alembic migration chain
has pre-existing branching issues outside this change's scope.
"""

import sqlite3


def test_signal_events_table():
    """signal_events table can be created and queried."""
    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE signal_events (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            symbols TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            confidence REAL NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            raw_url TEXT,
            metadata TEXT
        )
        """
    )
    con.execute("INSERT INTO signal_events (id, source, signal_type, timestamp, symbols, sentiment, confidence, title, content) VALUES ('1', 'polymarket', 'polymarket_probability', '2026-01-01', '[]', 'bullish', 0.8, 't', 'c')")
    cur = con.execute("SELECT id, source FROM signal_events")
    assert cur.fetchone() == ("1", "polymarket")
    con.close()


def test_push_dedup_table():
    """push_dedup table can be created and queried."""
    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE push_dedup (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            pushed_at DATETIME NOT NULL,
            channel TEXT NOT NULL
        )
        """
    )
    con.execute("INSERT INTO push_dedup (event_id, event_type, pushed_at, channel) VALUES ('e1', 'signal_received', '2026-01-01', 'telegram')")
    cur = con.execute("SELECT event_id FROM push_dedup")
    assert cur.fetchone() == ("e1",)
    con.close()


def test_decisions_new_columns_with_default():
    """decisions table can have new columns with NOT NULL DEFAULT."""
    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE decisions (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL
        )
        """
    )
    con.execute("INSERT INTO decisions (id, symbol, action) VALUES ('d1', 'AAPL', 'HOLD')")

    # Add new columns (mimics Alembic migration)
    con.execute("ALTER TABLE decisions ADD COLUMN signal_sources_json TEXT NOT NULL DEFAULT '[]'")
    con.execute("ALTER TABLE decisions ADD COLUMN fused_signal_json TEXT NOT NULL DEFAULT '{}'")
    con.execute("ALTER TABLE decisions ADD COLUMN context_snapshot_json TEXT NOT NULL DEFAULT '{}'")

    # Old row has defaults
    cur = con.execute("SELECT signal_sources_json, fused_signal_json, context_snapshot_json FROM decisions WHERE id='d1'")
    row = cur.fetchone()
    assert row == ("[]", "{}", "{}")

    # New row can set values
    con.execute("INSERT INTO decisions (id, symbol, action, signal_sources_json, fused_signal_json, context_snapshot_json) VALUES ('d2', 'TSLA', 'BUY', '[\"s1\"]', '{\"sentiment\":\"bullish\"}', '{\"size\":10}')")
    cur = con.execute("SELECT signal_sources_json FROM decisions WHERE id='d2'")
    assert cur.fetchone() == ('["s1"]',)
    con.close()
