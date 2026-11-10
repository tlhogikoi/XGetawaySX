# Local development

## Prerequisites
- Python 3.12+
- Node.js 22+
- PostgreSQL 16+ for shared development/staging. SQLite is used by default for a quick local backend smoke test unless DATABASE_URL is set.

## Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py test
python manage.py runserver
```

Health endpoint: http://127.0.0.1:8000/api/v1/health/

Copy the root `.env.example` to `.env` and configure values before running with PostgreSQL. Do not commit real credentials. The development fallback secret is not suitable for deployment.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

Production checks:

```bash
npm run typecheck
npm run build
```

## Current limitations

The initial frontend is a branded shell and the backend exposes only a health check. Authentication, partner onboarding, Gallery APIs, payment processing, AI integrations and deployment are not implemented yet.
