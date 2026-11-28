# XGetawaySX — Staging smoke-check report (Dev 67)

**Date:** 28 November 2026 (SAST)  
**Branch:** `feat/application-foundation`  
**Scope:** Staging deployment and API smoke checks only. Formal UAT has not started.

## Deployment baseline

| Component | Deployment | Result |
|---|---|---|
| Frontend | `xgetawaysx-staging-qempniko7-tlhogikoi.vercel.app` | READY |
| Backend | `xgetawaysx-api-staging-kxtvcmcfv-tlhogikoi.vercel.app` | READY |
| Neon connectivity | `/api/v1/health/ready/` | HTTP 200; database connected |
| Frontend direct routes | Home, About, Services, Trips, Gallery, Contact, Privacy, Help, Wishlist | HTTP 200 after SPA rewrite |

Frontend SPA rewrite commit: `df5ec8efd041a3bc8ddfa29eabba100b04514fb6`.

## API smoke-check results

| Endpoint | Observed result | Status |
|---|---:|---|
| `GET /api/v1/health/` | HTTP 200 | PASS |
| `GET /api/v1/health/ready/` | HTTP 200; database connected | PASS |
| `GET /api/v1/partners/` | HTTP 500 | BLOCKED |
| `GET /api/v1/partners/destinations/` | HTTP 500 | BLOCKED |
| `GET /api/v1/partners/collections/` | HTTP 500 | BLOCKED |
| `GET /api/v1/gallery/stories/` | HTTP 500 | BLOCKED |
| `GET /api/v1/accounts/me/` without a token | HTTP 401 expected for protected endpoint; deployment fetch tooling could not inspect response body | NOT FULLY VERIFIED |

## Root cause

Vercel runtime logs for the backend deployment `dpl_3Yk6DPzcqNudvTav8BFcXT3P6XGn` show PostgreSQL `UndefinedTable` errors. Missing relations include:

- `partners_partner`
- `partners_destinationpage`
- `partners_experiencecollection`
- `gallery_gallerymediapermissiongrant`

The database accepts connections, but the Django application schema is not fully migrated. A successful readiness query (`SELECT 1`) does not prove that application migrations have been applied.

## Remediation prepared

A guarded, manual GitHub Actions workflow was added:

`.github/workflows/staging-migrations.yml`

Commit: `a2ba996904a4eefd57cb700bcd64507acf1ca86d`.

The workflow:
1. Requires the exact manual confirmation text `APPLY STAGING MIGRATIONS`.
2. Requires the GitHub Actions secret `STAGING_DATABASE_URL_UNPOOLED`.
3. Rejects a Neon pooled hostname for schema migration use.
4. Prints the pending Django migration plan.
5. Runs `python manage.py migrate --noinput`.
6. Prints the resulting migration state.

**Required operator setup:** Add `STAGING_DATABASE_URL_UNPOOLED` in the repository's GitHub Actions secrets using the direct (non-`-pooler`) connection string for the XGetawaySX staging Neon database. Never paste the connection string into chat or commit it to the repository. Then run the workflow manually from `feat/application-foundation` and enter the required confirmation text.

## Frontend API configuration

The frontend previously had no Vercel environment variables. `CustomerAccount.tsx` reads `VITE_API_BASE_URL`; without it, account API calls default to the frontend origin. A Preview-only, branch-scoped `VITE_API_BASE_URL` has been added for `feat/application-foundation`, pointing to the staging API. It is present in the compiled frontend JavaScript. The frontend deployment `dpl_EqsKExYAqgLfixuAJQnqENNtFQRo` (commit `a2ba996`) is READY, and `/`, `/account/` and `/privacy-centre/` return HTTP 200. This verifies the API base URL is embedded in the build, but authenticated browser-to-API interaction still requires a real browser UAT.

## UAT decision

**UAT status: BLOCKED — NOT STARTED.**

Do not invite testers or create real bookings until:
- The staging migrations complete successfully.
- Partner, destination, collection and public Gallery API requests return expected responses.
- The new frontend deployment is READY and the compiled frontend contains the correct API base URL; authenticated account API requests still need browser verification.
- The frontend/backend smoke checks are repeated successfully.

Keep test data synthetic. Do not enable live payment capture, publish public Gallery content, or configure SMTP as part of this remediation.
