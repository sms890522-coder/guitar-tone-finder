from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock
from typing import Literal

DB_PATH = Path("stats.db")
_lock = Lock()

CounterName = Literal["tone_analysis", "tab_generation", "guide_download"]


def init_stats_db() -> None:
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS counters (
                    name TEXT PRIMARY KEY,
                    value INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            for name in ["tone_analysis", "tab_generation", "guide_download"]:
                conn.execute(
                    "INSERT OR IGNORE INTO counters (name, value) VALUES (?, 0)",
                    (name,),
                )

            conn.commit()
        finally:
            conn.close()


def increment_counter(name: CounterName, amount: int = 1) -> int:
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                "UPDATE counters SET value = value + ? WHERE name = ?",
                (amount, name),
            )
            conn.commit()

            row = conn.execute(
                "SELECT value FROM counters WHERE name = ?",
                (name,),
            ).fetchone()

            return int(row[0]) if row else 0
        finally:
            conn.close()


def get_stats() -> dict[str, int]:
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            rows = conn.execute("SELECT name, value FROM counters").fetchall()
            data = {str(name): int(value) for name, value in rows}

            return {
                "tone_analysis": data.get("tone_analysis", 0),
                "tab_generation": data.get("tab_generation", 0),
                "guide_download": data.get("guide_download", 0),
            }
        finally:
            conn.close()
