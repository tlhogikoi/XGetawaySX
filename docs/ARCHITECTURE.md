# XGetawaySX — Architecture & Development Plan

Status: Proposed architecture baseline. Validate against implementation as the repository is developed.

## Product domains
Identity/authentication and customer profiles; partner onboarding and dashboards; destinations, accommodation and experiences; Gallery; trip planning and managed quotations; group trips; bookings and payments; financial reconciliation; reviews; Concierge and AI; notifications; analytics and audit.

## Proposed stack
- Frontend: React, TypeScript and Vite.
- Backend: Django and Django REST Framework.
- Database: PostgreSQL.
- Realtime: WebSockets where required.
- Voice: WebRTC/telephony integration when implemented.
- AI: external model API behind server-side service boundaries.
- Media: object storage; store metadata, ownership and permission evidence in PostgreSQL.

## Architecture principles
1. Start with a modular monolith; avoid premature microservices.
2. Separate business domains into Django apps and frontend features.
3. Reuse one canonical user and partner identity model.
4. Enforce access control server-side for every private resource.
5. Use explicit workflow states and auditable transitions.
6. Never trust client-submitted payment status; verify signed gateway webhooks.
7. Keep customer funds, supplier liabilities, commissions, fees, tax and profit distinct.
8. Ground AI outputs in verified or owner-submitted facts.
9. Keep secrets out of Git and use environment/secret management.
10. Add migrations, automated tests and setup documentation with every milestone.

## Proposed Django apps
authentication, customers, partners, destinations, marketplace, gallery, trip_planning, group_trips, bookings, payments, financial_management, reviews, concierge, notifications, analytics and audit.

These are domain proposals, not evidence that the apps already exist.

## Proposed repository layout
XGetawaySX/ with frontend/, backend/, docs/, infrastructure/, .github/workflows/, .gitignore and README.md. Create frontend/backend scaffolding only after runtime versions and environment strategy are confirmed.

## Development sequence
1. Confirm stack versions, runtime requirements and environment strategy.
2. Create minimal frontend and backend applications with health checks.
3. Establish authentication and canonical partner/customer models.
4. Implement partner verification and role-based access.
5. Implement marketplace listings and media storage.
6. Implement Gallery foundations and approval workflow.
7. Add trips, itinerary planning and managed enquiries.
8. Add organised group departures, bookings and payment schedules.
9. Add financial ledger and gateway integration.
10. Add reviews, Concierge and AI assistance.
11. Add CI, staging, monitoring, backups and deployment controls.

## Quality gates
- Backend linting and Django checks pass.
- Migrations apply cleanly to a fresh PostgreSQL database.
- Unit and API tests pass.
- Frontend typecheck, lint and production build pass.
- Access-control tests prove partner isolation.
- Payment tests cover webhook authenticity and idempotency before payment launch.
- No secrets or personal data are committed.
- Claims about live partners, prices, availability and bookings are verified.

## Current baseline
The repository was confirmed empty before initialization. This document is a plan, not an implemented application or deployment.