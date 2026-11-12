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

## Current implementation status

- Backend foundations include the accounts, partner, health and Gallery Django apps.
- Partner listing and initial Gallery submission/review APIs are present on the `feat/application-foundation` branch.
- Gallery work remains in progress: version-bound approvals, separate original-history consent, formal media permission grants and editorial evidence review have been added on the feature branch; automated validation and PostgreSQL migration checks still need to be run.
- The frontend is a branded shell with an initial accessible Gallery story-card component; it is not yet connected to live Gallery API data.
- Initial private filesystem uploads for Gallery images and rights evidence are present on the feature branch. Set `PRIVATE_GALLERY_STORAGE_ROOT` to a writable directory outside all static/web roots before local use. Production S3-compatible object storage, malware scanning, image re-encoding and retention/backup controls are not complete.
- Partner story workspace, editorial UI, AI drafting, timelines, analytics, payments and deployment are not complete.
- The feature branch is not the production/default branch. Do not treat the Gallery as live or public until its tests, review and deployment gates pass.
