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
**Implementation status:** Initial backend permission-grant model, owner-only grant/revoke endpoints, publication-time active-grant checks, and focused tests have been added on `feat/application-foundation`. Evidence storage integration, legal wording, and test execution remain outstanding.

**Current API proposal implemented on the feature branch**
- `POST /api/v1/gallery/media/{media_id}/permissions/` — partner owner records the rights holder, permitted channels, private evidence reference and optional expiry.
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

**Dependencies:** partner identity; media storage/evidence retention decision; legal review of permission wording.

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
5. Do not launch media upload until storage, file validation, access control and permission evidence retention are agreed.
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
