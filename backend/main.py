from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from analyzer import analyze_audio
from recommender import recommend_tone

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


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="MP3, WAV, M4A, AAC, FLAC, OGG 파일만 지원합니다.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="파일은 25MB 이하로 업로드해주세요.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        analysis = analyze_audio(tmp_path)
        rec = recommend_tone(analysis)
        return {"analysis": analysis, "recommendation": rec}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"분석에 실패했습니다: {exc}") from exc
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
