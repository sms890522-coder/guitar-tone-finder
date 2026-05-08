from __future__ import annotations
from stats_store import get_stats, increment_counter, init_stats_db
import asyncio
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from analyzer import analyze_audio
from recommender import recommend_tone
from tab_analyzer import analyze_tab
from queue_manager import (
    create_job,
    get_all_queued_job_ids,
    get_job,
    update_job,
    worker_loop,
)

app = FastAPI(title="Guitar Tone Finder API")

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://guitar-tone-finder.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


async def process_queued_job(job_id: str, job: dict):
    payload = job.get("payload", {})
    tmp_path = payload.get("tmp_path")
    filename = payload.get("filename")
    job_type = job.get("type")

    if not tmp_path:
        raise RuntimeError("작업 파일이 없습니다.")

    try:
        
        
        if job_type == "analyze":
            update_job(job_id, progress=30)

            analysis = analyze_audio(tmp_path)

            update_job(job_id, progress=75)

            rec = recommend_tone(analysis)

            increment_counter("tone_analysis")
            
            update_job(
                job_id,
                status="done",
                progress=100,
                result={
                    "ok": True,
                    "filename": filename,
                    "analysis": analysis,
                    "recommendation": rec,
                },
            )

        elif job_type == "tab":
            update_job(job_id, progress=30)

            tab_result = analyze_tab(tmp_path)
            increment_counter("tab_generation")
            update_job(
                job_id,
                status="done",
                progress=100,
                result={
                    "ok": True,
                    "filename": filename,
                    "tab_analysis": tab_result,
                },
            )

        else:
            raise RuntimeError(f"알 수 없는 작업 타입입니다: {job_type}")

    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@app.on_event("startup")
async def startup_event():
    init_stats_db()
    asyncio.create_task(worker_loop(process_queued_job))


@app.post("/analyze-queue")
async def analyze_queue(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="MP3, WAV, M4A, AAC, FLAC, OGG 파일만 지원합니다.",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="파일은 25MB 이하로 업로드해주세요.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        job_id = create_job(
            "analyze",
            {
                "tmp_path": tmp_path,
                "filename": file.filename,
            },
        )

        return {
            "ok": True,
            "job_id": job_id,
            "status": "queued",
            "message": "분석 작업이 대기열에 추가되었습니다.",
        }

    except RuntimeError as exc:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        raise HTTPException(status_code=429, detail=str(exc)) from exc


@app.post("/tab-queue")
async def tab_queue(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="MP3, WAV, M4A, AAC, FLAC, OGG 파일만 지원합니다.",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="파일은 25MB 이하로 업로드해주세요.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        job_id = create_job(
            "tab",
            {
                "tmp_path": tmp_path,
                "filename": file.filename,
            },
        )

        return {
            "ok": True,
            "job_id": job_id,
            "status": "queued",
            "message": "타브 생성 작업이 대기열에 추가되었습니다.",
        }

    except RuntimeError as exc:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        raise HTTPException(status_code=429, detail=str(exc)) from exc


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    queue_position = 0

    if job.get("status") == "queued":
        queued_jobs = get_all_queued_job_ids()

        if job_id in queued_jobs:
            queue_position = queued_jobs.index(job_id) + 1

    return {
        "job_id": job_id,
        "type": job.get("type"),
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "result": job.get("result"),
        "error": job.get("error"),
        "queue_position": queue_position,
    }


# 선택: 기존 프론트 호환용 즉시 분석 API
@app.post("/analyze")
async def analyze_direct(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="MP3, WAV, M4A, AAC, FLAC, OGG 파일만 지원합니다.",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="파일은 25MB 이하로 업로드해주세요.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        analysis = analyze_audio(tmp_path)
        rec = recommend_tone(analysis)

        return {
            "ok": True,
            "filename": file.filename,
            "analysis": analysis,
            "recommendation": rec,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"분석에 실패했습니다: {exc}") from exc

    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# 선택: 기존 프론트 호환용 즉시 타브 API
@app.post("/tab-analyze")
async def tab_analyze_direct(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="MP3, WAV, M4A, AAC, FLAC, OGG 파일만 지원합니다.",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="파일은 25MB 이하로 업로드해주세요.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        tab_result = analyze_tab(tmp_path)

        return {
            "ok": True,
            "filename": file.filename,
            "tab_analysis": tab_result,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"타브 분석에 실패했습니다: {exc}") from exc

    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@app.get("/stats")
async def stats():
    return {
        "ok": True,
        "stats": get_stats(),
    }


@app.post("/stats/guide-download")
async def count_guide_download():
    value = increment_counter("guide_download")

    return {
        "ok": True,
        "guide_download": value,
        "stats": get_stats(),
    }



