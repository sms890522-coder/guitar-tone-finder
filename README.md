# ToneScope AI - Guitar Tone Finder MVP

오디오 파일을 업로드하면 Python/librosa 기반으로 기타톤 특징을 분석하고, 비슷한 앰프·이펙터 체인과 세팅값을 추천하는 1차 MVP입니다.

## Stack

- Frontend: Next.js App Router + Tailwind CSS
- Backend: FastAPI
- Audio Analysis: librosa, numpy, scipy

## Local Run

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```txt
http://localhost:3000
```

## Environment

Frontend에서 백엔드 URL을 바꾸려면 `frontend/.env.local` 생성:

```env
BACKEND_URL=http://localhost:8000
```

## MVP Limitations

- 처음 버전은 실제 장비명을 정확히 식별하지 않습니다.
- 오디오 특징 기반 추정값으로 비슷한 톤을 만드는 출발점 세팅을 제공합니다.
- Demucs 기타 stem 분리는 2차 버전에서 추가하는 것을 추천합니다.
