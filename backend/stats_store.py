from __future__ import annotations

import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def get_stats() -> dict[str, int]:
    response = (
        supabase.table("app_stats")
        .select("name,value")
        .in_("name", ["tone_analysis", "tab_generation"])
        .execute()
    )

    stats = {
        "tone_analysis": 0,
        "tab_generation": 0,
    }

    for row in response.data or []:
        stats[row["name"]] = int(row["value"])

    return stats


def increment_counter(name: str) -> int:
    if name not in ["tone_analysis", "tab_generation"]:
        raise ValueError("허용되지 않은 카운터 이름입니다.")

    response = supabase.rpc("increment_stat", {"counter_name": name}).execute()

    if response.data is None:
        return get_stats().get(name, 0)

    return int(response.data)


def init_stats_db() -> None:
    # Supabase에서는 앱 시작 때 SQLite 초기화가 필요 없음
    return