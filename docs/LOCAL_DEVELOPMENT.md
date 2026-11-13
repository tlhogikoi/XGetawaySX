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
- An initial authenticated `PartnerGalleryWorkspace` React component is present on the feature branch. The host partner portal must supply the bearer access token and partner context; no sign-in/session integration or route mounting is implemented yet. Editorial media review UI, AI drafting, timelines, analytics, payments and deployment are not complete.
- The feature branch is not the production/default branch. Do not treat the Gallery as live or public until its tests, review and deployment gates pass.


## Payment gateway sandbox setup

The backend supports hosted checkout adapters for PayFast and Yoco. Copy the payment variables from `.env.example` into your local environment and use sandbox/test credentials only.

- PayFast: configure merchant ID/key, passphrase, sandbox mode and a publicly reachable HTTPS `PAYFAST_NOTIFY_URL`.
- Yoco: configure a test secret key and the webhook subscription signing secret. Register the webhook at `https://<public-host>/api/v1/partners/webhooks/yoco/`.
- Set the customer return/cancel/failure URLs. A browser return is not payment confirmation; verified provider webhook/ITN processing updates payment status.
- Local webhook testing requires a public HTTPS tunnel or deployed staging host. Never expose live secrets or store card details in XGetawaySX.

Provider account setup, sandbox transactions, webhook delivery tests and live activation are separate release gates; the presence of configuration variables does not mean a gateway account is connected.
