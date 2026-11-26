# XGetawaySX — Pre-Test Release Checklist

Status: preparation checklist for the first controlled South African test cycle. This document is not evidence that staging, provider accounts, live inventory or production payments are configured.

## Test objective
Validate the implemented customer, partner, booking, payment-workflow and Gallery journeys with controlled South African test partners and test customers before any public launch.

## 1. Release gates before testers are invited
- [ ] Latest feature-branch CI passes on PostgreSQL 16, including Django checks, migration drift check, fresh migrations, backend tests, frontend typecheck and production build.
- [ ] Reconcile the feature branch with the current `main` branch; confirm the pull request is mergeable and obtain approval before merging.
- [ ] Deploy a staging build from the reviewed commit. Confirm the frontend and backend point to staging services, not production.
- [ ] Configure a strong staging-only Django secret, allowed hosts, CORS origins, database, private Gallery storage and HTTPS.
- [ ] Configure PayFast and/or Yoco sandbox credentials and publicly reachable HTTPS webhook endpoints. Keep live credentials disabled.
- [ ] Create synthetic test customers, partner owners, staff reviewers and approved test partner listings. Do not use real customer identity or payment data.
- [ ] Prepare approved test prices, availability, cancellation terms, refund rules and test trip content. Clearly label all test inventory.
- [ ] Verify database backup and restore procedure for staging before test data is collected.

## 2. Functional test journeys

### Customer account and discovery
- [ ] Register with valid details; verify duplicate email and invalid password handling.
- [ ] Sign in, sign out, refresh an expired access token and view only the signed-in customer account.
- [ ] Browse destinations and partner listings; confirm unapproved or inactive partner records are not publicly exposed.
- [ ] Check responsive layout and navigation on a current mobile browser and desktop browser.

### Partner onboarding and verification
- [ ] Partner owner can view only their own partner profiles and onboarding submissions.
- [ ] Submit the required business details and evidence documents; reject incomplete submissions.
- [ ] Staff can access the review queue and approve, request changes or reject a submitted application.
- [ ] Verify the owner can see the decision, review notes and activity history after signing in. Outbound email delivery is deferred until after first UAT.
- [ ] Verify private evidence downloads are restricted to the owning partner and authorised staff; test cross-account access denial.
- [ ] Confirm an approved partner is not automatically Gallery-published or booking-enabled unless the separate approval state permits it.

### Enquiries, quotes and reservations
- [ ] Customer submits an enquiry and the correct partner can view and respond to it.
- [ ] Convert an eligible enquiry to a quote/reservation and verify customer/partner ownership boundaries.
- [ ] Check quote totals, currency, dates, guest counts, payment schedule and terms before acceptance.
- [ ] Test deposit and balance/installment schedules, due dates, reminders and overdue states.
- [ ] Test reservation confirmation, cancellation and refund request paths, including invalid state transitions.

### Payments and refund audit
- [ ] Use sandbox transactions only; never use live card details during this test cycle.
- [ ] Verify checkout creation and provider return handling.
- [ ] Verify signed PayFast ITN / Yoco webhook processing, duplicate-event idempotency and rejection of invalid signatures.
- [ ] Confirm a browser return alone never marks a reservation as paid.
- [ ] Test successful, failed, pending and duplicate payment events.
- [ ] Test refund outcomes and verify refund records, provider references, reconciliation state and in-app audit history. Outbound email delivery is deferred until after first UAT.
- [ ] Reconcile reservation amount, paid amount, refund amount and outstanding balance.

### Gallery and content permissions
- [ ] Only approved partner entities, approved media and published story versions appear publicly.
- [ ] Verify owner consent and editorial approval apply to the same story version.
- [ ] Verify a material edit invalidates prior approvals until the revised version is approved.
- [ ] Confirm original owner history, rights evidence, private notes and internal review data remain private unless separately authorised.
- [ ] Confirm placeholder or unapproved partner content is not presented as real approved inventory.

## 2A. UAT regression scenarios

Record each scenario in the test evidence register. Use synthetic accounts and test reservations only.

- [ ] **UAT-RES-01 — Customer isolation:** Customer A cannot view, cancel or decide a quotation for Customer B's reservation, even when the reservation ID is known.
- [ ] **UAT-RES-02 — Partner isolation:** Partner A cannot quote, confirm, decline or inspect Partner B's reservation.
- [ ] **UAT-RES-03 — Invalid transitions:** A cancelled or declined reservation cannot be cancelled, quoted or confirmed again.
- [ ] **UAT-RES-04 — Capacity race:** Two requests competing for the same remaining capacity cannot both be confirmed beyond capacity.
- [ ] **UAT-RES-05 — Status audit:** Creation, withdrawal and partner decision entries show the correct status transition, actor role, timestamp and reason.
- [ ] **UAT-RES-06 — Cancellation workflow:** A confirmed booking with captured payment remains active until the sandbox refund is fully reconciled; cancellation completion must not release capacity prematurely.
- [ ] **UAT-PAY-01 — Browser return safety:** A customer browser return without a verified provider webhook does not mark a payment as captured.
- [ ] **UAT-PAY-02 — Late payment notification:** A valid PayFast or Yoco success notification received after its reservation is cancelled is rejected for manual investigation; it must not capture the payment, create a commission entry or silently restore the booking.
- [ ] **UAT-PAY-03 — Sequential partial refunds:** Reconcile two partial sandbox refunds for one captured payment; verify cumulative refunds never exceed the capture, commission reversals total correctly, duplicate webhook delivery creates no second adjustment/notification, and payment becomes fully refunded only when the cumulative refund equals the captured amount.
- [ ] **UAT-GAL-01 — Gallery approval gates:** Partner verification alone does not publish media or stories; owner consent and editorial approval must match the current content version.
- **UAT-GAL-02 — Rights withdrawal after publication:** publish an approved story in staging, then revoke the media permission as the partner owner; the story must disappear from list/detail responses and its image endpoint must return 404 on the next request.

## 3. Security, reliability and usability checks
- [ ] Test role-based access for customer, partner owner and staff roles, including direct API requests.
- [ ] Test cross-partner and cross-customer ID substitution on private endpoints.
- [ ] Validate upload type/size restrictions and private storage access.
- [ ] Check form validation, error messages, empty states, loading states and retry behaviour.
- [ ] Check keyboard navigation, visible focus, labels, contrast and mobile overflow on core journeys.
- [ ] Confirm secrets, tokens, evidence files and payment data do not appear in frontend bundles or application logs.
- [ ] Record defects with severity, reproducible steps, expected result, actual result and screenshot/log evidence.

## 4. Test boundaries for this cycle
- SMTP configuration and outbound email delivery are explicitly deferred until after the first UAT cycle. Do not block UAT on a verified sender, SMTP credentials or mailbox setup. In-app status, notifications and audit records must be used where available.
- AI trip suggestions, AI story drafting and multilingual AI/human Concierge must be marked out of scope unless their provider integration and user-facing workflow are separately completed and verified.
- No real customer bookings, live payment capture, live refunds or public Gallery publication during internal testing.
- A passing CI run does not prove that live payment provider accounts, email delivery, staging deployment or real partner inventory are operational.

## 5. Exit criteria
- [ ] All release gates in section 1 are complete.
- [ ] All critical and high-severity defects are fixed and retested.
- [ ] All core customer, partner, staff, reservation and payment sandbox journeys have recorded pass/fail evidence.
- [ ] No cross-account access-control failures remain.
- [ ] Payment and refund records reconcile with provider sandbox events.
- [ ] Product owner signs off the test report and the explicitly supported launch scope.

## Test evidence register
Record each run with: test ID, tester, date/time, environment/build commit, browser/device, test data ID, result, defect reference and evidence link.