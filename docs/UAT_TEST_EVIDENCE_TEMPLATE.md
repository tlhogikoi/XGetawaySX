# XGetawaySX — UAT Test Evidence Template

**Purpose:** Capture reproducible evidence for the first controlled South African user-acceptance test cycle.

> Use staging only. Use synthetic customer, partner and staff accounts. Do not enter real identity documents, live payment credentials or real customer data. SMTP remains out of scope for this first UAT cycle.

## 1. Test cycle details

| Field | Value |
|---|---|
| Test cycle / release | |
| Environment URL | |
| Frontend deployment URL | |
| Backend deployment URL | |
| Git branch | |
| Commit SHA | |
| Database branch / environment | |
| Test window (SAST) | |
| Test lead | |
| Testers | |
| Browser / device matrix | |

## 2. Test execution register

Record one row per execution. Repeat a test row when it is retested after a fix.

| Test ID | Tester | Date/time (SAST) | Build commit | Browser/device | Synthetic data ID | Result (Pass/Fail/Blocked) | Defect ID | Evidence link |
|---|---|---|---|---|---|---|---|---|
| UAT-RES-01 | | | | | | | | |
| UAT-RES-02 | | | | | | | | |
| UAT-RES-03 | | | | | | | | |
| UAT-RES-04 | | | | | | | | |
| UAT-RES-05 | | | | | | | | |
| UAT-RES-06 | | | | | | | | |
| UAT-RES-07 | | | | | | | | |
| UAT-PAY-01 | | | | | | | | |
| UAT-PAY-02 | | | | | | | | |
| UAT-PAY-03 | | | | | | | | |
| UAT-PAY-04 | | | | | | | | |
| UAT-GAL-01 | | | | | | | | |
| UAT-GAL-02 | | | | | | | | |
| UAT-GAL-03 | | | | | | | | |
| UAT-GAL-04 | | | | | | | | |
| UAT-GAL-05 | | | | | | | | |

## 3. Individual test execution record

Copy this section for each test execution.

- **Test ID / title:**
- **Tester:**
- **Date and time (SAST):**
- **Environment and deployment commit:**
- **Browser / device / OS:**
- **Synthetic account and record IDs:**
- **Preconditions:**
- **Steps performed:**
  1.
  2.
  3.
- **Expected result:**
- **Actual result:**
- **Result:** Pass / Fail / Blocked
- **Evidence links:** screenshots, redacted logs, request IDs or screen recording
- **Defect reference (if failed):**
- **Retest result and commit (if applicable):**

## 4. Defect report

- **Defect ID:**
- **Summary:**
- **Severity:** Critical / High / Medium / Low
- **Affected role and journey:**
- **Environment / commit:**
- **Preconditions and synthetic data IDs:**
- **Steps to reproduce:**
- **Expected behaviour:**
- **Actual behaviour:**
- **Evidence:**
- **Workaround:**
- **Assigned owner:**
- **Fix commit / PR:**
- **Retest outcome:**
- **Status:** Open / In progress / Fixed awaiting retest / Closed

Do not attach secrets, access tokens, payment card data or unredacted personal information to defect reports.

## 5. Daily test summary

| Metric | Count / notes |
|---|---|
| Tests executed | |
| Passed | |
| Failed | |
| Blocked | |
| Critical defects open | |
| High defects open | |
| Regression tests pending | |
| Environment incidents | |

### Blockers and decisions
-

### Risks accepted for this test cycle
-

### Next test session
-

## 6. Exit review and sign-off

- [ ] All release gates in `PRE_TEST_RELEASE_CHECKLIST.md` reviewed.
- [ ] Critical and high-severity defects are fixed and retested.
- [ ] Customer and partner isolation checks passed.
- [ ] Reservation, cancellation and payment sandbox reconciliation evidence reviewed.
- [ ] Gallery rights withdrawal, suspension, version approval and immutable revision checks reviewed.
- [ ] No live payments, public Gallery publication or real customer bookings were used.
- [ ] Remaining defects and out-of-scope items documented and accepted by the product owner.

| Sign-off role | Name | Decision (Approve / Reject / Conditional) | Date (SAST) | Notes |
|---|---|---|---|---|
| Product owner | | | | |
| Test lead | | | | |
| Technical lead | | | | |

**UAT outcome:** Not started / In progress / Passed with conditions / Failed

**Important:** A completed template is evidence of test execution only when it contains actual tester, environment, timestamp, result and supporting evidence. A passing CI or deployment status is not a substitute for UAT.
