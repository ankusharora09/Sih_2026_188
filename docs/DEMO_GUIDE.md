# Demo Guide

This guide walks through setting up and running the SIH 2026 Identity Screening demo.

## Prerequisites
- Python 3.12+ installed.
- `git` and `docker` (optional for containerized run).
- Environment variables (see `.env.example`).

## Setup
```bash
# Clone the repository (already present)
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Database
By default the app uses SQLite (`sqlite:///./dev.db`). For PostgreSQL set `DATABASE_URL`:
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/identity
```
Run migrations if applicable (not included in this demo).

## Redis (optional for rate‑limit)
Set `REDIS_URL` if you want Redis‑backed rate limiting:
```bash
export REDIS_URL=redis://localhost:6379/0
```

## Run the API
```bash
uvicorn backend.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

## Create demo cases
A helper script is provided to generate ten synthetic cases with random images.
```bash
python scripts/create_demo_cases.py
```
It will:
1. Create a new case via the API.
2. Upload a synthetic document image (random noise).
3. Optionally upload a live‑capture image.
4. Trigger the screening pipeline.
5. Log the resulting `ScreeningRun` IDs.

## Front‑end dashboard
If you have a web server (e.g., Nginx) serving `frontend/`, open the dashboard at:
```
http://localhost:8000/frontend/index.html
```
It fetches `/api/v1/cases` and displays status, risk level, and a link to view details.

## Performance benchmark
Run the benchmark script to measure stage latencies on synthetic data:
```bash
python tests/performance/benchmark.py
```
It prints a short report and writes `performance_report.txt`.

## Expected output
After running the demo you should see:
- Cases listed at `/api/v1/cases`.
- Each case shows `status` (`completed`/`failed`).
- Risk level (`low`/`medium`/`high`).
- Explanation text from Ollama or fallback.

## Cleanup
To reset the demo environment:
```bash
rm -rf uploads dev.db
```
