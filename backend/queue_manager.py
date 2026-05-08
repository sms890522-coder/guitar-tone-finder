from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Awaitable, Callable

JobStatus = dict[str, Any]

jobs: dict[str, JobStatus] = {}
queue: asyncio.Queue[str] = asyncio.Queue()

MAX_QUEUE_SIZE = 20


def get_all_queued_job_ids() -> list[str]:
    queued = [
        (job_id, job)
        for job_id, job in jobs.items()
        if job.get("status") == "queued"
    ]

    queued.sort(key=lambda item: float(item[1].get("created_at", 0)))

    return [job_id for job_id, _ in queued]


def create_job(job_type: str, payload: dict[str, Any]) -> str:
    if len(get_all_queued_job_ids()) >= MAX_QUEUE_SIZE:
        raise RuntimeError("현재 대기열이 가득 찼습니다. 잠시 후 다시 시도해 주세요.")

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "type": job_type,
        "status": "queued",
        "progress": 0,
        "created_at": time.time(),
        "updated_at": time.time(),
        "payload": payload,
        "result": None,
        "error": None,
    }

    queue.put_nowait(job_id)

    return job_id


def get_job(job_id: str) -> JobStatus | None:
    return jobs.get(job_id)


def update_job(job_id: str, **kwargs: Any) -> None:
    if job_id not in jobs:
        return

    jobs[job_id].update(kwargs)
    jobs[job_id]["updated_at"] = time.time()


def cleanup_old_jobs(max_age_seconds: int = 60 * 30) -> None:
    now = time.time()

    old_job_ids = [
        job_id
        for job_id, job in jobs.items()
        if now - float(job.get("created_at", now)) > max_age_seconds
    ]

    for job_id in old_job_ids:
        jobs.pop(job_id, None)


async def worker_loop(
    process_job: Callable[[str, JobStatus], Awaitable[None]],
) -> None:
    while True:
        job_id = await queue.get()

        try:
            job = jobs.get(job_id)

            if not job:
                continue

            update_job(job_id, status="processing", progress=10)

            await process_job(job_id, job)

        except Exception as exc:
            update_job(
                job_id,
                status="failed",
                progress=100,
                error=str(exc),
            )
        finally:
            queue.task_done()
            cleanup_old_jobs()
            
