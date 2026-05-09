from __future__ import annotations

import os
from typing import Any

from supabase import Client, create_client


_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase

    if _supabase is not None:
        return _supabase

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise RuntimeError("Supabase 환경변수가 설정되지 않았습니다.")

    _supabase = create_client(url, key)
    return _supabase


def init_stats_db() -> None:
    """
    Supabase에서는 SQL Editor에서 테이블을 만들기 때문에
    여기서는 연결 확인 정도만 한다.
    """
    get_supabase()


def get_stats() -> dict[str, int]:
    supabase = get_supabase()

    response = (
        supabase.table("app_stats")
        .select("key,value")
        .in_("key", ["tone_analysis", "tab_generation"])
        .execute()
    )

    rows: list[dict[str, Any]] = response.data or []

    stats = {
        "tone_analysis": 0,
        "tab_generation": 0,
    }

    for row in rows:
        key = str(row.get("key"))
        value = int(row.get("value") or 0)

        if key in stats:
            stats[key] = value

    return stats


def increment_counter(key: str) -> int:
    if key not in {"tone_analysis", "tab_generation"}:
        raise ValueError(f"지원하지 않는 카운터입니다: {key}")

    supabase = get_supabase()

    response = supabase.rpc(
        "increment_stat",
        {
            "stat_key": key,
        },
    ).execute()

    return int(response.data or 0)