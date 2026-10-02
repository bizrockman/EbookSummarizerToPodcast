# Two-Tier Run Guide

## 1. Backend (FastAPI + Huey Worker)

1. Install Python dependencies:
```powershell
pip install -r requirements_api.txt
```

2. Choose one startup mode:

Option A (recommended): all-in-one dev starter
```powershell
python start_dev.py
```

Option B: separate processes in two terminals
Terminal 1 (API):
```powershell
python start_api.py
```
Terminal 2 (worker only):
```powershell
python -m huey.bin.huey_consumer api.config.huey_config.huey -w 1 -k thread
```

Backend base URL: `http://localhost:8000`

## 2. Frontend (Next.js + Tailwind)

1. Go to frontend:
```powershell
cd frontend
```
2. Install dependencies:
```powershell
npm install
```
3. Copy env file:
```powershell
Copy-Item .env.example .env.local
```
4. Run frontend:
```powershell
npm run dev
```

Frontend URL: `http://localhost:3000`

## 3. Default Local Credentials

- API key header is preconfigured in frontend env:
  - `NEXT_PUBLIC_API_KEY=dummy-api-key-12345`
- You can test backend endpoints directly with the same key in `X-API-Key`.

## 4. Frontend Pages

- `/` dashboard:
  - books list
  - recent jobs
  - tracked total cost and active job counts
- `/workflow`:
  - EPUB upload
  - KI-Kapitelanalyse mit Autoauswahl
  - Kapitel manuell anpassen
  - Audiobook-Job starten und Status verfolgen
- `/jobs/{job_id}` detail:
  - live job status fields
  - full job event timeline from `GET /jobs/{job_id}/events`

## 5. Next Build Step

This baseline is intentionally thin but production-oriented:
- It already consumes the async job API and timeline events.
- Next implementation step is adding creation forms for:
  - upload/register book
  - `POST /audiobook/basic`
  - `POST /audiobook/chapters`
  - upcoming translated/summary jobs.
