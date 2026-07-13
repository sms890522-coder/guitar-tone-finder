from __future__ import annotations

import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def init_stats_db() -> None:
    # Supabase에서는 테이블을 SQL Editor에서 미리 만들기 때문에 여기서는 아무것도 안 해도 됨
    return


def get_stats():
    default_stats = {
        "tone_analysis": 0,
        "tab_generation": 0,
    }

    try:
        response = (
            supabase
            .table("app_stats")
            .select("*")
            .execute()
        )

        stats = default_stats.copy()

        for row in response.data or []:
            name = row.get("name")
            value = row.get("value", 0)

            if name in stats:
                stats[name] = int(value or 0)

        return stats

    except Exception as error:
        print(f"[STATS] Supabase 통계 조회 실패: {error}")

        # Supabase가 멈춰도 앱이 죽지 않도록 기본값 반환
        return default_stats


def increment_counter(name: str) -> int:
    if name not in ["tone_analysis", "tab_generation"]:
        raise ValueError(f"Unknown counter name: {name}")

    current = get_stats().get(name, 0)
    new_value = current + 1

    response = (
        supabase.table("app_stats")
        .upsert(
            {
                "name": name,
                "value": new_value,
            },
            on_conflict="name",
        )
        .execute()
    )

    print("INCREMENT RESPONSE:", response.data)

    return new_value
