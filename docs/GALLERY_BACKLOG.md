# XGetawaySX Gallery — Delivery Backlog

Status: implementation planning artifact. This backlog records approved product rules separately from implementation proposals. It does not mean the listed work is deployed or production-ready.

## 1. Approved product rules

These are product decisions, not proposals:

1. The Gallery is a promotional showcase for XGetawaySX-approved partner entities only. A partner's Gallery approval is separate from its enquiry and booking approvals.
2. Each Gallery image can have its own story. One partner may therefore have multiple image/story pairs.
3. Hover, keyboard focus and touch activation reveal the same concise 30–60-word summary.
4. Selecting the image/story opens the relevant partner profile or story.
5. The owner's original history is private by default. Publishing that original history requires a separate, explicit permission in addition to approval of the story summary.
6. AI may edit, organise, translate or summarise facts supplied by the owner or verified sources. It must not invent dates, people, founders, cultural origins, awards, events or milestones.
7. AI output is a draft only. The owner must approve the exact story version and an authorised editor must approve that same version before publication.
8. Publication requires current partner Gallery approval, valid media rights and promotional permission, both approvals, and a final publication-time eligibility check.
9. A material edit creates a new version and invalidates approvals for the previous version.
10. Public APIs must not expose private original history, evidence references, internal notes or non-public partner information.

## 2. Repository baseline observed

Inspected on the feature branch `feat/application-foundation`:

- Django apps for accounts, partners, gallery and health exist; the canonical user and partner models are already present.
- Gallery models currently include `GalleryMedia`, `GalleryStory`, `GalleryStoryRevision` and `GalleryAuditEvent`.
- Basic DRF public-story, media submission, story submission, owner approval, editorial approval, draft, revision and audit views exist.
- A public partner list exists, but a partner detail/profile API has not been established.
- React/Vite/TypeScript includes a branded landing page, `GalleryPartnerGrid` and `GalleryStoryCard`.
- The landing page currently passes an empty stories array; the public Gallery is not yet connected to the API.
- The card now uses a stable story ID, reveals on hover/focus/tap, closes on pointer exit or focus leaving the card, and supports Escape. Device and screen-reader QA remains outstanding.
- No AI provider/service, media object-storage integration, partner story workspace, editorial queue, timeline or Gallery analytics implementation was found.
- An earlier malformed story-submission statement was corrected on this feature branch. Version-bound approval fields, a separate version-scoped original-history consent record/action, and related tests have since been added. Migration 0003 is present, but backend tests, migration checks and CI have not yet been confirmed passing.

## 3. Prioritised implementation backlog

### P0 — Make publication safe and testable

#### G0.1 Repair and validate the existing Gallery API
**Tasks**
- Repair the malformed story-submission view code.
- Remove response-shape manipulation from the revision list and rely on a serializer that explicitly excludes private snapshots.
- Verify Gallery URL inclusion on the feature branch without prematurely exposing unfinished routes on the default branch.
- Run Django system checks, migration drift checks, migrations and the full backend test suite.

**Acceptance criteria**
- Python imports and Django checks succeed.
- `makemigrations --check --dry-run` reports no model/migration drift.
- Fresh-database migrations apply.
- Public, owner and editorial endpoints return documented status codes and response shapes.

**Dependencies:** existing accounts and partner apps.

#### G0.2 Version-bound approvals and separate original-history consent
**Tasks**
- Add a monotonically increasing story content version.
- Record the version approved by the owner and the version approved by editorial.
- Add a separate, auditable original-history publication consent tied to a specific story version, including grant/revocation actor and timestamps.
- Keep original history private on creation and on every material edit.
- Remove permission flags from ordinary draft writes; only the dedicated owner-consent action may grant or revoke publication permission.
- Make editorial publication reject mismatched or missing approval versions and recheck all eligibility conditions.
- Treat revisions as content snapshots only; approval events belong in the audit log and must not create artificial content versions.

**Acceptance criteria**
- An owner approval cannot authorise a later edited version.
- Editorial approval cannot publish a version other than the exact owner-approved version.
- Approving a summary does not grant permission to publish original history.
- Only the owning partner can grant/revoke original-history publication consent.
- A grant applies only to the current story version; a material edit returns original history to private by default.
- Revocation immediately removes original history from public responses without requiring story-summary unpublication.

**Dependencies:** G0.1; canonical partner owner identity.

#### G0.3 Formal media-rights records
**Implementation status:** Permission-grant model, owner-only grant/revoke endpoints, editorial evidence review, private local file storage, multipart uploads, and gated image/evidence delivery have been added on `feat/application-foundation`. Automated validation, malware scanning, production object storage, legal wording and PostgreSQL checks remain outstanding.

**Current API proposal implemented on the feature branch**
- `POST /api/v1/gallery/media/{media_id}/permissions/` — partner owner uploads the actual rights evidence document with the rights holder, permitted channels and optional expiry.
- `POST /api/v1/gallery/media/{media_id}/permissions/{grant_id}/revoke/` — partner owner revokes a grant.
- `POST /api/v1/gallery/media/{media_id}/permissions/{grant_id}/review/` — authorised editorial staff approve/reject the private evidence.
- The public API never returns the private evidence reference.
- A grant must be editorially approved, active, unrevoked and unexpired at publication and public-query time.

**Tasks**
- Replace client-trusted rights booleans/timestamps as the sole evidence with a `MediaPermissionGrant` record.
- Record rights holder, permitted channels/uses, evidence reference, granting actor, granted-at, expiry and revocation.
- Keep the evidence reference private to the partner owner and authorised editorial/legal roles.
- Require an active Gallery promotional grant at submission review and again at publication.
- Add a withdrawal path that immediately removes affected media/story from public results.

**Acceptance criteria**
- Missing, expired, out-of-scope or revoked permission blocks approval and publication.
- Public serializers never return evidence references or internal permission notes.
- A rights withdrawal is audited and removes the media from public Gallery results.

**Dependencies:** partner identity; private media storage and evidence retention; legal review of permission wording.


#### G0.3.1 Private media and evidence upload subsystem

**Implementation status:** Initial private filesystem implementation is committed on `feat/application-foundation`; it is suitable for local/staging validation only and is not a production object-storage integration.

**Implemented on the feature branch**
- Added private `FileField` storage for partner images and rights evidence, using randomised storage names and a storage root outside static/media URL serving.
- Added upload validation for file size and JPEG, PNG, WebP image signatures; PDF is also accepted for rights evidence.
- Added multipart media and permission-evidence upload paths.
- Added an authenticated evidence download endpoint limited to the owning partner or authorised staff, with private/no-store headers and an audit event.
- Added public image delivery only after partner, media, story, version approvals and active rights checks pass. Uploaded images are not directly exposed through storage URLs.
- Added tests for private evidence access, image gating, and unsupported image content.

**Remaining tasks**
- Replace local filesystem storage with a durable private S3-compatible object-storage backend for deployed environments; configure private bucket policy, encryption, lifecycle/retention, backups and access logging.
- Add malware scanning/quarantine and full image decoding/re-encoding before editorial approval.
- Add upload quotas, rate limiting, image dimension/pixel limits, and operational cleanup for abandoned uploads.
- Validate reverse-proxy request limits and ensure the private storage directory is never mounted or aliased by Nginx/static hosting.
- Confirm whether rights evidence needs a legal retention schedule and support multiple rights holders/releases per image.

**Acceptance criteria**
- Unapproved files have no public URL and cannot be retrieved anonymously.
- Evidence can be retrieved only by the owning partner or authorised editorial staff.
- An uploaded image is publicly retrievable only while every publication gate remains valid; delivery uses no-store caching to avoid stale access after revocation.
- Unsupported file signatures and over-limit files are rejected.
- Evidence review cannot be approved without an uploaded evidence file.
- Production storage is private, durable, encrypted and independently access-logged before launch.

**Dependencies:** G0.3; production hosting/storage decision; malware-scanning service; legal retention policy.

#### G0.4 Partner and editorial access controls
**Tasks**
- Use explicit permission classes/services for partner owner, explicitly assigned partner staff, Gallery editor, Gallery publisher and administrator.
- Enforce partner ownership in querysets and object-level actions, not only in UI controls.
- Separate editorial review from final publishing authority if operational staffing requires it.
- Add audit events for submit, edit, request-changes, approve, reject, suspend, publish, unpublish and rights withdrawal.

**Acceptance criteria**
- Partner A cannot read, edit, approve or retrieve revisions for Partner B.
- Ordinary staff without the Gallery role cannot publish.
- An editor cannot impersonate the owner or grant owner consent.
- Every privileged transition records actor, object, version, action and timestamp.

**Dependencies:** accounts/role design; G0.2 and G0.3.

#### G0.5 Public Gallery and partner profile API
**Tasks**
- Add paginated `GET /api/v1/gallery/` and public story detail endpoints.
- Add `GET /api/v1/partners/{slug}/` for approved public partner profiles.
- Include only approved partners, approved media, published stories and active permissions.
- Return a stable story ID, partner slug, image URL, alt text, title and summary.
- Keep Gallery approval distinct from enquiry/booking eligibility.

**Acceptance criteria**
- Pending, rejected or suspended partners never appear.
- A suspended partner or withdrawn media permission disappears from public results on the next request.
- Each image/story resolves to the correct partner profile or story.
- Pagination and filtering do not leak private records.

**Dependencies:** G0.2–G0.4; media delivery decision.

### P1 — Deliver the public and operational user experience

#### G1.1 API-connected React Gallery
**Tasks**
- Add typed Gallery API client, response types, loading, empty and error states.
- Replace the hard-coded empty `stories={[]}` prop with API data.
- Build `GalleryPage`, `GalleryGrid`, `GalleryStoryCard`, `StoryOverlay` and `PartnerProfilePage`.
- Add category/location filters only after supported API fields are defined.

**Acceptance criteria**
- Public cards contain only API-returned approved stories.
- Every image has descriptive alt text.
- The story CTA opens the correct story or partner profile.
- Empty, loading, API-failure and no-results states are usable and branded.

**Dependencies:** G0.5; frontend API base URL/CORS configuration.

#### G1.2 Accessible hover, focus, touch and keyboard behaviour
**Tasks**
- Reveal the same 30–60-word summary on hover, focus and tap.
- Close hover-only reveal when the pointer leaves, without hiding content while keyboard focus remains inside the card.
- Support Escape to close; preserve predictable focus.
- Use unique stable IDs from story records, not title-derived IDs.
- Use semantic buttons for reveal and links for navigation; remove duplicate mobile-only controls.
- Respect reduced-motion preferences and provide visible focus indicators.

**Acceptance criteria**
- Keyboard-only users can reveal, read and follow the story link.
- Touch users can reveal the summary and activate the story/profile link.
- Escape closes the reveal without moving focus unexpectedly.
- Screen readers receive meaningful labels and expanded/collapsed state.
- No interaction depends exclusively on hover.

**Dependencies:** G1.1; final story-card navigation contract.

#### G1.3 Partner story workspace
**Tasks**
- Build `PartnerStoryManager`, `PartnerStoryEditor`, `OriginalHistoryForm`, `StoryMediaUploader`, `MediaPermissionPanel`, `StoryVersionHistory`, `StoryPreview` and `StoryApprovalPanel`.
- Show current state, missing requirements and the exact version awaiting approval.
- Make the separate original-history publication permission a distinct, clearly worded action.
- Provide a preview of the public 30–60-word summary and image/story destination.

**Acceptance criteria**
- Partner users only see their own entities and content.
- Original history is labelled private and never preselected for publication.
- Owner approval is explicit and tied to the displayed version.
- A changed draft visibly returns to owner review.

**Dependencies:** G0.2–G0.4; authentication/session handling; media storage.

#### G1.4 Editorial review and publishing queue
**Tasks**
- Build `EditorialReviewQueue`, `StoryReviewPanel`, `MediaRightsReviewPanel`, `ChangesRequestedForm` and publish/suspend controls.
- Display source facts, AI-assistance disclosure, version comparison and rights status.
- Require the publisher to recheck partner approval, active media permission and version approvals immediately before publishing.

**Acceptance criteria**
- Editors cannot publish without owner approval of the current version.
- Publishers cannot publish with missing/expired/revoked rights.
- Rejected, suspended and changes-requested items are not public.
- Editorial actions are audited.

**Dependencies:** G0.2–G0.4; notification service for review requests.

### P2 — Enrich stories and measure performance

#### G2.1 AI-assisted story drafting
**Tasks**
- Implement a server-side drafting service behind a provider interface; keep provider keys out of the frontend and repository.
- Accept owner-supplied history and structured facts, with optional verified references.
- Return proposed 30–60-word summary, source-fact mapping, unsupported-claim warnings and missing-information questions.
- Store prompt/model/version metadata and the exact input revision used.
- Require human owner review; AI must have no approval or publish permission.

**Acceptance criteria**
- Every generated factual statement maps to supplied or verified source material.
- Unsupported dates, people, founders, cultural claims, awards and milestones are flagged or omitted.
- AI output cannot change approval state or publish content.
- Failed/uncertain generations remain drafts and are clearly labelled AI-assisted.

**Dependencies:** provider selection, secret management, privacy/retention review, source-fact schema. No provider is assumed to be configured.

#### G2.2 Partner profiles and optional story timelines
**Tasks**
- Add public partner profile sections for approved description, category, location and published image/story collection.
- Add optional `StoryTimelineEvent` with title, description, date and date precision (exact, month/year, year-only, approximate).
- Keep timeline events private until the story version is approved; allow source/reference attachment privately.
- Add timeline editor and accessible chronological presentation.

**Acceptance criteria**
- Profiles show only Gallery-approved public fields.
- Timeline is optional and never blocks a valid story without dates.
- Approximate dates are labelled as approximate; unknown dates are not fabricated.
- Each image can still open its own story even when a timeline exists.

**Dependencies:** G0.5; G1.3; verified source/reference policy.

#### G2.3 Privacy-conscious Gallery analytics
**Tasks**
- Record distinct events for impressions, reveal activations, story/profile clicks, enquiries, related-trip clicks and verified completed bookings.
- Define event deduplication, consent/retention and attribution windows before dashboards.
- Add partner-facing aggregated analytics and internal editorial performance views.
- Never equate an impression with an engaged read or completed booking.

**Acceptance criteria**
- Metrics distinguish impressions, interactions, enquiries and verified bookings.
- Partners see only their own permitted aggregate data.
- No private original history or sensitive source evidence is sent to analytics.
- Events are tested for duplicate firing and missing identifiers.

**Dependencies:** G1.1; event/consent design; enquiry/booking systems for downstream attribution.

## 4. Cross-cutting automated test matrix

- Model/migration: fresh database, upgrade path, migration drift, unique version and consent constraints.
- Permissions: anonymous public access; owner isolation; other-owner denial; staff/editor/publisher separation.
- Publication: approved partner + approved media + active rights + same-version owner/editorial approvals.
- Privacy: original history private by default; no private fields in public or ordinary revision serializers; consent grant/revoke and version scoping.
- AI: grounded facts only, unsupported claim warnings, no automatic approval/publish, provider failure handling.
- Frontend: hover enter/leave, focus/blur, touch tap, Escape, stable IDs, route target, reduced motion and screen-reader semantics.
- Integration: API pagination, loading/error/empty states, partner suspension, rights expiry/revocation and publication race checks.
- CI: Django check, migration drift, full backend suite, frontend typecheck and production build.

## 5. Delivery gates and dependencies

1. Do not expose Gallery routes on the default branch until G0.1–G0.4 tests pass.
2. Do not wire public frontend data until G0.5 response contracts are stable.
3. Do not enable AI drafting until a provider, privacy controls and source-fact schema are approved.
4. Do not publish extended owner history until a separate version-bound consent record exists.
5. Do not launch media upload publicly until production private object storage, malware scanning, file validation, access control and permission evidence retention are agreed.
6. Do not launch booking attribution until the booking system can provide verified completion events.

## 6. Definition of done

A Gallery release is ready for controlled staging only when the P0 acceptance criteria and relevant automated tests pass, frontend typecheck/build pass, the migration path is verified against PostgreSQL, and a manual owner/editor/visitor accessibility walkthrough is recorded. Production release additionally requires legal review of rights/consent wording, operational editorial roles, backups, monitoring and an approved deployment plan.


## 7. Feature-branch implementation update — media permissions

The following work is present on `feat/application-foundation`; it has not been merged or deployed:

- Added `GalleryMediaPermissionGrant` with rights holder, Gallery-promotion purpose, permitted channels, private evidence reference, granting actor/time, optional expiry and revocation actor/time.
- Added migrations `0004_gallery_media_permission_grants.py` and `0005_media_permission_editorial_review.py`.
- Added owner-only permission grant and revocation endpoints, plus an editorial evidence-review endpoint.
- Editorial media approval and story publication require a formally recorded grant that has passed editorial evidence review.
- Public Gallery queries exclude media with missing, pending, rejected, revoked or expired grants.
- Added focused tests for grant/revoke, owner isolation, expired permissions and revoked permissions.
- Registered permission records as read-only in Django admin.

**Remaining validation and integration work**
- Run Django checks, migration drift checks, fresh PostgreSQL migrations and the full backend suite.
- Confirm the installed Django version supports the migration constraint syntax.
- Connect evidence references to private object storage with access logging, retention and upload validation; a text reference alone is not proof that evidence exists.
- Have legal review the rights-holder declaration, permitted channels, expiry and withdrawal wording.
- Decide whether the legacy rights booleans can be deprecated after existing records are reconciled.
- Add an editorial UI for reviewing permission evidence without exposing it to public APIs or unauthorised partner users.
- Confirm whether one permission record can cover all rights holders for a media asset, or whether the data model must support multiple independently required rights holders and releases.


## 8. Feature-branch implementation update — private uploads

The following code has been committed to `feat/application-foundation`; it has not been merged or deployed:

- Added `GalleryMedia.image_file` and `GalleryMediaPermissionGrant.evidence_file` using a private filesystem storage backend.
- Added upload size/signature validators and randomised storage paths.
- Added multipart upload support for partner media and rights evidence.
- Added owner/staff-only evidence retrieval with no-store headers and audit logging.
- Added public image delivery guarded by partner approval, media approval, published story, current owner/editorial version approvals and active rights permission.
- Corrected the accidental placement of media-rights review fields on the original-history consent model; those fields belong to `GalleryMediaPermissionGrant`.
- Added migrations `0006_private_gallery_file_storage.py` and `0007_legacy_image_url_optional.py` and focused upload/access tests.

**Not yet complete:** CI/test execution, PostgreSQL migration validation, malware scanning, image decode/re-encode, durable private object storage, production bucket policy, retention/backup policy, upload quotas and deployment configuration.

## 9. Partner Gallery workspace — implementation update

**Status:** Initial React/TypeScript workspace component and responsive styling are committed to `feat/application-foundation`. It is a reusable authenticated component, not yet mounted as a route or deployed.

**Files**
- `frontend/src/components/PartnerGalleryWorkspace.tsx`
- `frontend/src/components/partner-gallery.css`

**Current capabilities**
- Requires an access token and partner context to be supplied by the host partner portal; it does not create or store credentials.
- Uploads a partner image through the existing multipart media endpoint.
- Uploads rights evidence and selected permitted channels through the permission-grant endpoint.
- Creates one 30–60-word story for the uploaded image.
- Keeps owner original history private by default and does not expose an in-workspace publication toggle.
- Lists the authenticated owner's story drafts and exposes owner approval only after partner and media approval are both reported as approved.
- Displays the required publication checklist and keeps editorial approval as a staff-only backend action.

**API contract additions**
- The authenticated story draft serializer now returns `media_status` and `partner_gallery_status` so the workspace can accurately reflect the approval gates.

**Integration requirements before mounting**
- Connect the component to the actual partner authentication/session provider and pass a short-lived bearer access token, partner ID, partner display name and Gallery approval state.
- Confirm the deployed API base URL and CORS/auth configuration.
- Add a partner portal route and navigation only after the authentication shell is available.
- Add frontend unit/component tests and run TypeScript typecheck + Vite production build.
- Add editorial-side media evidence review and media approval UI; those actions must remain unavailable to partner users.
- Add story editing/versioning and explicit version-bound original-history consent controls as a separate owner action after legal/product review.

**Acceptance criteria**
- Unauthenticated users cannot load partner data or submit content.
- Partner owners can only submit content against their own partner record; backend authorization remains authoritative.
- Image and evidence uploads use multipart requests; private storage URLs are never exposed.
- Owner history remains private unless separate explicit consent is recorded for the current story version.
- Owner approval is enabled only after partner and media approval; publication still requires separate editorial approval.
- A content edit invalidates previous approvals and requires both approvals again.

**Not yet verified:** No frontend build, browser test, backend test run, PostgreSQL migration run, merge or deployment has been completed in this phase.



## Development 4 — Editorial Review Dashboard

- Added the staff-only `GET /api/v1/gallery/editorial/queue/` endpoint. It returns pending rights-evidence grants, media awaiting approval after rights verification, and stories awaiting editorial review.
- Queue payloads are intentionally minimised: original owner history and revision snapshots are not returned. AI source facts are included only as the story's explicitly supplied fact list for reviewer verification.
- Added `frontend/src/components/EditorialGalleryDashboard.tsx` and `editorial-gallery.css`. The dashboard supports private evidence download, approve/reject decisions for rights evidence, media approval, story publication, queue refresh and recent audit activity.
- Existing backend review actions remain the source of truth and enforce staff access, active evidence, partner approval, and current-version owner approval. Evidence access is separately audited.
- Integration remains pending: mount the dashboard inside the authenticated staff route and pass the staff access token. The public-facing `App.tsx` is intentionally unchanged.
- Verification status: backend tests were added for staff-only queue access and exclusion of private owner history. No test suite, TypeScript build, migration, merge or deployment has been run as part of this change.
- Known workflow limitation: story editorial approval currently supports publication approval only; a formal story return/rejection workflow with partner resubmission semantics remains a separate task. Rights evidence supports both approval and rejection.


## Development 5 — Story editing and editorial revision workflow

**Committed on `feat/application-foundation`; not merged or deployed.**

- Added staff-only `POST /api/v1/gallery/stories/{id}/request-changes/`. Editors must provide a reason (10–1,000 characters); the action is audited with the story version and reason.
- A returned story moves to the partner's `rejected` / “Changes requested” state. Its previous owner/editorial approvals and publication timestamp are cleared.
- Updated partner draft editing access so the owner can revise a returned story. A material edit creates a new immutable revision record and increments the story version; the story returns to owner review and requires fresh owner approval and subsequent editorial approval.
- Added partner workspace controls to edit the public summary and private original history, view safe revision history, and respond to requested changes.
- Added editorial dashboard controls to request changes with a documented reason or approve/publish the current owner-approved version.
- Revision history shown to partners contains summary/version metadata only; private original-history snapshots and internal AI source-fact snapshots are not exposed by the revision serializer.

**Automated tests added:** staff-only change requests, required reason/audit details, denial of partner-initiated editorial actions, and partner revision of a returned story with fresh version/approval gates.

**Not yet verified:** Django test suite, TypeScript typecheck, Vite build, browser workflow, PostgreSQL migrations, CI, merge and deployment. No database migration was introduced by this stage.

**Workflow note:** editorial request-changes is available only while a story is awaiting editorial review. Published stories are not editable through the current partner draft endpoint; any post-publication correction/withdrawal process requires a separate controlled workflow.


## Development 6 — Partner notifications and review communication

**Committed on `feat/application-foundation`; not merged or deployed.**

- Added `GalleryPartnerNotification` for in-app notices addressed to the owning partner account, with story reference, notification kind, timestamp and read state.
- Added authenticated partner endpoints: `GET /api/v1/gallery/notifications/` and `POST /api/v1/gallery/notifications/{id}/read/`.
- Notification queries and read actions are scoped to both the authenticated recipient and the partner owner. Other partner accounts cannot view or mark another owner's notice as read.
- Editorial publication creates a partner notification that the story is now published.
- Editorial request-changes creates a partner notification containing the specific feedback intended for that partner. Internal audit history and private owner history are not included in notification payloads.
- Added notification list, unread count, timestamps and mark-as-read interaction to `PartnerGalleryWorkspace`.
- Added automated tests for owner-only listing, cross-partner denial and read-state updates.

**Delivery boundary:** these are in-app notifications only. Email, SMS, push notifications, background delivery/retries and notification preferences are not configured or claimed. The existing component remains a reusable workspace awaiting host portal route/auth integration.

**Not yet verified:** Django test suite, migration application/drift, TypeScript typecheck, Vite production build, browser workflow and CI. No merge or deployment has been performed.


## Development 7 — Partner activity timeline and submission tracking

**Committed on `feat/application-foundation`; not merged or deployed.**

- Added owner-scoped `GET /api/v1/gallery/partners/{partner_id}/activity/`.
- The activity feed presents the latest 100 audit milestones with event label, media/story references, safe version number and timestamp.
- Supported milestones include media submission, rights evidence submission/review/revocation, media approval, story submission, owner approval, edits, editorial change requests and publication.
- The API deliberately does not serialise arbitrary audit `details`, private owner history, evidence contents, review notes or internal editorial comments.
- Partner owners can only view their own partner activity; unauthorised partner access is denied. Staff can inspect activity for a partner through the same endpoint.
- Added activity timeline UI to the partner workspace and refreshes it after upload, rights submission, story creation/editing, owner approval and manual refresh.
- Added tests for owner access, cross-partner denial, anonymous access and omission of private audit details.

**Delivery boundary:** this is an audit-event timeline, not a separate configurable workflow engine. The feed is limited to the latest 100 events and depends on workflow actions continuing to write audit records. It does not expose staff-only internal notes or promise email/push alerts.

**Not yet verified:** Django tests/checks, migration application/drift, TypeScript typecheck, Vite production build, browser accessibility, CI, merge or deployment.


## Development 8 — Editorial quality control and version comparison

**Implemented on `feat/application-foundation`; not merged or deployed.**

- Added staff-only, version-bound quality reviews for factual claims, owner-supplied source facts, unsupported claims and image/context accuracy.
- Internal reviewer notes are stored with the review record and excluded from partner/public serializers.
- Publishing requires a passing quality review for the exact current story version, alongside the existing owner approval, partner/media approval and active evidence-backed rights permission.
- Extended the editorial queue with the version number carrying a passing quality review.
- Added a dashboard checklist, internal notes and a safe revision comparison using summary/version metadata only. Private original-history snapshots remain excluded.
- Added tests for staff-only access, required checks, stale-version rejection and the publication gate.
- Added migration `0009_gallery_story_editorial_quality_review.py`.

**Not yet verified:** Django tests/checks, migration application/drift, PostgreSQL upgrade path, frontend typecheck/build, browser workflow, CI, merge or deployment.

## Development 9 — Public partner profiles and Gallery integration

**Implemented on `feat/application-foundation`; not merged or deployed.**

- Added public partner detail API `GET /api/v1/partners/{slug}/`. It returns only Gallery-approved partner profile fields and that partner's stories from the existing fully gated public Gallery queryset.
- Partner profiles hidden from Gallery or in pending/suspended/rejected approval states return 404. Owner IDs, enquiry/booking approval states and internal account fields are not serialised.
- Connected the homepage Gallery grid to `GET /api/v1/gallery/stories/`, with loading, empty and error states. Each image retains its individual 30–60-word story reveal and links to the associated partner profile.
- Added a public partner profile page with approved description, category, location, optional website link and its published story collection.
- The profile story collection uses the same public story serializer and does not include private original history unless the existing separate, current-version consent gate allows it.
- Added partner profile API tests for approved visibility, hidden unapproved profiles and omission of internal fields.

**Integration boundary:** direct `/partners/{slug}/` navigation requires the production host to serve the React app fallback for this route. Configure the backend API origin through `VITE_API_BASE_URL` when frontend and API are hosted on different origins.

**Not yet verified:** Django tests/checks, frontend typecheck/build, browser navigation, CORS and production route fallback, CI, merge or deployment.

## Development 10 — Public-facing unpublished-content placeholders

**Implemented on `feat/application-foundation`; not merged or deployed.**

- Added a reusable branded `GalleryContentPlaceholder` component for public empty states.
- Replaced the Gallery empty state with neutral wording that invites visitors to return for new stories.
- Replaced the empty partner-story message with a compact version of the same placeholder.
- Placeholder copy does not disclose whether content is awaiting partner approval, rights review, owner approval, editorial review, or has been returned for changes.
- Public Gallery and partner-profile APIs remain the source of truth: only eligible approved/published content is rendered. The placeholder does not reveal unpublished records or internal workflow status.

**Not yet verified:** frontend typecheck/build, component/browser tests, backend tests, CI, merge, deployment and production visual QA.


## Development 11 — Partner discovery, search and filtering

**Implemented on `feat/application-foundation`; not merged or deployed.**

- Extended `GET /api/v1/partners/` with optional `q`, `category`, `city`, `province` and `country` filters.
- Search matches approved partner name, description, city and province. Category values are restricted to the model's declared category choices; text inputs are trimmed and bounded.
- The approved-partner queryset remains the base queryset before every filter. Pending, rejected and suspended partners are never returned by public discovery.
- Added a responsive public discovery interface with keyword search, category and destination filters, result count, loading/error/empty states and direct links to public partner profiles.
- Partner cards show only fields already permitted by `PublicPartnerSerializer`; profile pages continue to obtain stories from the publication-gated Gallery queryset.
- Updated the main navigation to point to the discovery section.

**API examples**
- `/api/v1/partners/?q=mountain`
- `/api/v1/partners/?category=accommodation&city=Johannesburg`
- `/api/v1/partners/?province=Gauteng&country=South%20Africa`

**Not yet verified:** Django test suite, frontend typecheck/build, browser and accessibility tests, CI, pagination/performance under production data, merge and deployment.


## Development 12 — Destination pages and curated experience collections

**Implemented on `feat/application-foundation`; not merged or deployed.**

- Added editorially managed `DestinationPage` and `ExperienceCollection` records, with publication flags, stable slugs, display ordering and optional partner associations.
- Added Django admin management for destination guides and curated collections. Editors can assign partner records and explicitly publish/unpublish each page or collection.
- Added public APIs:
  - `GET /api/v1/partners/destinations/`
  - `GET /api/v1/partners/destinations/{slug}/`
  - `GET /api/v1/partners/collections/`
  - `GET /api/v1/partners/collections/{slug}/`
  - Collections may be filtered by a published destination slug using `?destination={slug}`.
- Public destination pages and collections return only explicitly published records. Associated partner lists are independently filtered to Gallery-approved partners; a pending, rejected or suspended partner cannot appear through a curated association.
- Collections attached to an unpublished destination are excluded from public list and detail endpoints. Collections without a destination can still be published independently.
- Added destination index/detail and curated collection detail views in the React app, linked from homepage navigation. Partner cards link to their existing approved public profiles.
- Added backend tests for unpublished destination/collection hiding, approved-partner filtering and destination publication boundaries.

**Editorial boundary:** destinations and collections are curated editorial content, not automatically generated destination facts or booking inventory. No map, pricing, availability, booking, ratings or partner endorsement claims are inferred. A destination/collection is not public until an editor explicitly publishes it.

**Not yet verified:** migration application, Django checks/test suite, frontend typecheck/build, browser route fallback, CI, merge or deployment.


## Development 13 — Trip planning and partner enquiry management

**Implemented on `feat/application-foundation`; not merged or deployed.**

### Data and access controls
- Added private `TripPlan` records owned by the authenticated customer, with title, notes and optional travel dates.
- Added `TripPlanItem` associations to approved partners. A partner must also have enquiry approval before being added to a plan, and a partner can appear only once per plan.
- Added `PartnerEnquiry` records linking the customer, one partner and optionally the customer's trip plan. Enquiries store the customer's message, requested dates, partner response and lifecycle status.
- Trip plans and customer enquiry history are owner-scoped. Partner inbox and response actions are scoped to the owner of the receiving partner.
- Public partner discovery accepts `?enquiry_ready=true` for the trip planner's partner picker without exposing the partner's internal enquiry approval status as a public field.

### API
- `GET/POST /api/v1/partners/trips/` — list the current user's plans or create a plan.
- `GET/PATCH/DELETE /api/v1/partners/trips/{id}/` — retrieve, update or delete an owned plan.
- `POST /api/v1/partners/trips/{id}/items/` — add an approved, enquiry-ready partner.
- `DELETE /api/v1/partners/trips/{id}/items/{item_id}/` — remove an item from an owned plan.
- `GET/POST /api/v1/partners/enquiries/` — list the customer's enquiries or submit a partner enquiry.
- `GET /api/v1/partners/partner/enquiries/` — list enquiries for the authenticated partner owner.
- `POST /api/v1/partners/partner/enquiries/{id}/respond/` — accept or decline a pending enquiry with a written response.

### Frontend workspaces
- Added reusable authenticated `TripPlanner` component for creating plans, saving approved partners, setting dates, sending individual partner enquiries and tracking enquiry status.
- Added reusable `PartnerEnquiryDashboard` for partner owners to review requests and accept or decline with a response.
- Both components receive a bearer access token from the host authentication/session provider. They are intentionally not mounted as public routes because this repository does not yet expose a confirmed customer/partner authentication shell to supply that token safely.

### Product boundary
- Enquiries are not bookings, reservations, confirmed availability or payments. A partner's acceptance records an enquiry response only; it does not confirm a reservation.
- Each partner receives only its own enquiry. Customer contact email is visible only to the customer and the receiving partner owner through authenticated enquiry endpoints.
- The current workflow is synchronous in-app API delivery. Email/SMS/push notifications, partner response SLAs, booking inventory, deposits and payments are not included.

### Tests and verification
- Added tests for private trip-plan ownership, adding approved partners, rejection of non-approved partners, enquiry submission tied to an owned plan, partner response and cross-partner access denial.
- Added a test for the enquiry-ready discovery filter.
- Migration `0003_trip_plans_and_partner_enquiries.py` created.
- **Not yet verified:** Django checks/tests, migration application/drift, frontend typecheck/build, authenticated browser workflow, CI, merge or deployment.

## Development 14 — Booking & Reservation Management Foundation

Implemented on `feat/application-foundation`:

- Added `PartnerAvailability` daily inventory records with partner ownership, date, guest capacity, reserved guest count, open/closed state and optional per-guest price/currency.
- Added unique partner/date and booked-capacity database constraints.
- Added `ReservationRequest` with customer, partner, optional trip plan, check-in/start date, exclusive checkout/end date, guest count, status, partner response and a UUID booking reference.
- Added public availability lookup, partner-owned availability management, customer reservation request/history, partner reservation inbox/decision and customer cancellation endpoints.
- A request remains pending until the partner confirms it. Confirmation runs in a database transaction, locks the request and each daily availability row, rechecks capacity for every requested night, increments reserved capacity and issues a booking reference.
- Declining a pending request does not consume capacity. Cancelling a confirmed reservation releases the reserved guest capacity.
- Added booking-ready partner discovery filtering without exposing internal booking approval status in the public partner serializer.
- Added reusable authenticated React customer reservation and partner reservation/availability workspaces. These are not mounted into the public app because the repository still has no confirmed shared authentication/session integration; each component accepts a host-provided bearer token.

### API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v1/partners/availability/?partner_id=&start_date=&end_date=` | Public date-specific availability |
| GET, POST | `/api/v1/partners/partner/availability/` | Partner-owned availability records |
| GET | `/api/v1/partners/partner/profiles/` | Booking-approved profiles owned by the authenticated partner |
| GET, POST | `/api/v1/partners/reservations/` | Customer reservation history and request creation |
| POST | `/api/v1/partners/reservations/{id}/cancel/` | Customer cancellation |
| GET | `/api/v1/partners/partner/reservations/` | Partner reservation inbox |
| POST | `/api/v1/partners/partner/reservations/{id}/decision/` | Partner confirmation or decline |

Reservation date semantics: the start date is included and the end/checkout date is excluded. Capacity is counted as guests per date, not rooms or units. The partner must publish availability for every requested night. The confirmation transaction protects capacity using row locks on databases that support `SELECT FOR UPDATE`; production deployment should use PostgreSQL. No payment, deposit, automatic expiry, external calendar sync, email/SMS notifications, refund or channel-manager integration is implemented. Prices are informational only and no payment is collected.

Tests were added for pending requests, capacity reservation on confirmation, capacity rechecking, cancellation capacity release and partner ownership. They have **not** been executed. The migration has **not** been applied or checked against a live database; frontend typecheck/build and browser testing have **not** been run. No CI, merge or deployment is claimed.

## Development 15 — Payments, Deposits & Booking Financial Management

Implemented on `feat/application-foundation`:

- Added `PartnerFinancialSettings` for partner deposit policy (none, percentage or fixed amount), currency and a platform-managed commission rate. Partner owners can update deposit policy; commission rate is read-only in the partner API and managed by platform administrators.
- Added `ReservationPayment` records linked to confirmed reservations, customers and partners. Records carry a server-calculated amount, currency, payment kind (deposit/balance/full), status, idempotency key, provider name/reference and capture timestamp.
- Added `PartnerCommissionLedger` entries created when an administrator reconciles a payment as captured. Each captured payment can create only one commission entry; gross, commission and partner-net amounts are stored as a financial snapshot.
- Added a server-side payment preparation endpoint. It calculates the reservation total from each reserved night’s published per-guest price multiplied by the guest count, requires consistent currency and complete pricing, then applies the partner’s deposit policy. A pending payment record is created; no payment is collected by this endpoint.
- Added admin-only payment reconciliation. A captured result requires an external provider reference; capture is blocked if the reservation is no longer confirmed. Reconciliation is idempotent for the same final status and provider reference.
- Added partner-owned financial settings and summary endpoints, including captured totals and commission ledger entries.
- Added Django admin views for partner availability, reservations, financial settings, payment records and commission ledger. Payment and commission ledger records are read-only in admin to keep financial state changes within reconciliation.
- Added customer payment history/preparation and partner finance dashboard React components. These are reusable authenticated components and are not mounted into the app until the shared authentication/session integration is available.
- Added safeguards: payment preparation only for confirmed reservations; captured payments block cancellation until a refund workflow exists; a cancelled reservation cannot subsequently be marked captured; customer idempotency keys prevent duplicate payment records; partner commission rate cannot be changed through partner endpoints.

### API routes

| Method | Route | Purpose |
|---|---|---|
| GET, POST | `/api/v1/partners/payments/` | Customer payment history and payment record preparation |
| POST | `/api/v1/partners/payments/{id}/reconcile/` | Admin-only reconciliation of an external payment result |
| GET, POST | `/api/v1/partners/partner/financial-settings/` | Partner-owned deposit policy |
| GET | `/api/v1/partners/partner/financial-summary/?partner_id=` | Partner captured totals and commission ledger |

### Financial and payment boundaries

- This is a payment-record and reconciliation foundation, **not a payment gateway**. No card details are collected or stored; no checkout redirect, tokenisation, payment webhook, bank transfer or settlement is implemented.
- The payment preparation endpoint creates a pending record with a server-computed amount. An administrator may reconcile it only after verifying the transaction in an external payment provider. Never mark a record captured solely because a customer submitted the request.
- Prices are calculated as per-guest nightly prices multiplied by guests and nights. This does not yet model room/unit inventory, taxes, discounts, add-ons, variable occupancy pricing or multi-currency exchange.
- Commission is calculated and accrued at capture time using the platform-managed rate. Payouts, bank account details, disbursements, statements, refunds and chargebacks are not implemented. Captured reservations cannot be cancelled through the current cancellation endpoint until a refund workflow is provided.
- The payment status includes a refunded state for future lifecycle compatibility, but no refund endpoint is available in this development.

### Verification

- Added tests for server-calculated deposit amount, idempotent payment preparation, rejection of unconfirmed reservations, admin-only reconciliation, commission ledger calculation, partner commission-rate protection, and cancellation/capture safeguards.
- Migration `0005_partner_finance_and_reservation_payments.py` created.
- **Not yet verified:** Django checks/tests, migration application/drift, frontend typecheck/build, browser workflow, CI, merge or deployment. No real payment provider is connected.

