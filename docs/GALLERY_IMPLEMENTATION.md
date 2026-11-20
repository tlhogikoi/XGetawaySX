# XGetawaySX Gallery — Implementation Specification

Status: Product specification. Delivery progress, implemented scaffolding, dependencies and acceptance criteria are tracked separately in [GALLERY_BACKLOG.md](GALLERY_BACKLOG.md). This document is not evidence of a live or deployed Gallery.

## 1. Purpose
The Gallery is an official promotional showcase for approved XGetawaySX partner entities only. It is not a public upload gallery or traveller photo-sharing feature. It may showcase approved accommodation providers, tourism businesses, destinations, activities, restaurants, spas, transport providers and other approved entities.

Gallery advertising approval is separate from approval to receive marketplace enquiries or online bookings.

## 2. Approved story experience
- Each displayed image may have its own story.
- Desktop hover reveals the story summary.
- Keyboard focus reveals the same summary.
- Touch tap reveals the summary.
- Summary length: approximately 30–60 words.
- Selecting the image or explicit story link opens the relevant partner profile or story.
- Full history is private by default. Public extended history requires separate, explicit publication permission.
- Story content must remain accessible without relying exclusively on hover.

## 3. AI safeguards
AI may edit, organise, translate or summarise partner-supplied facts. It must not invent founders, dates, people, cultural origins, events, awards or historical milestones. AI output is draft-only and cannot approve or publish. Preserve original owner-submitted history and record the source version used for every generated draft. Flag unsupported claims and missing information.

## 4. Approval and publication
Publication requires current partner Gallery approval, owner/authorised representative approval of the exact story version, editorial approval of that same version, valid media usage permission and successful content/accessibility checks. The publisher must recheck all conditions at publication time.

Suggested states: draft, submitted, ai_processing, owner_review, owner_approved, editorial_review, changes_requested, editorial_approved, ready_to_publish, published, suspended, rejected, archived.

A material edit creates a new version and invalidates approvals for the previous version. Any low-risk editorial correction exception must be separately documented.

## 5. Proposed Django models
- GalleryCategory: name, slug, description, active.
- PartnerMedia: partner, storage key, media type, caption, alt text, status.
- PartnerStory: partner, title, original history, public summary, extended story, publication scope, status.
- StoryVersion: story, version number, content snapshot, author, change reason.
- StoryMedia: story, media, display order, image-specific caption.
- StoryTimelineEvent: story, title, description, date, date precision.
- StoryReference: story, reference type, description, secure evidence reference.
- MediaPermission: media, rights holder, permitted uses, evidence, expiry, withdrawal.
- StoryApproval: story version, approver, approval type, decision, timestamp.
- StoryAuditLog: actor, action, record, timestamp, metadata.

Reuse canonical authentication and partner models. Do not create duplicate user or partner tables. Keep private original history and public story fields separate in API serializers and access policies.

## 6. Proposed API
Public: GET /api/v1/gallery/ ; /categories/ ; /featured/ ; /stories/{slug}/ ; /partners/{slug}/ ; /promotions/.
Partner: GET/POST /api/v1/partners/me/stories/ ; PATCH /stories/{id}/ ; POST /stories/{id}/submit/ ; POST /stories/{id}/approve/ ; GET /stories/{id}/versions/ ; POST /media/ ; POST /media/{id}/permissions/.
Editorial: GET /api/v1/admin/gallery/review-queue/ ; POST /stories/{id}/approve/ ; /reject/ ; /suspend/ ; POST /media/{id}/approve/ ; GET /audit/.
These are proposed API contracts and may be adjusted to match the eventual partner and authentication implementation.

## 7. Permissions
- Visitor/customer: published public Gallery content only.
- Partner owner: own partner stories, media, references and approvals only.
- Partner staff: explicitly granted actions only.
- Gallery editor: review and request changes.
- Gallery publisher: publish only after all checks pass.
- Administrator: controlled, audited administrative access.

Every partner-scoped query must enforce ownership server-side. Public serializers must exclude original history, private references, internal notes and non-public contact information.

## 8. React/TypeScript components
Public feature: GalleryPage, PartnerStoryPage, PartnerProfilePage, GalleryHeader, GalleryNavigation, GallerySearch, GalleryFilters, FeaturedPartners, GalleryGrid, GalleryStoryCard, StoryOverlay, StoryTimeline, PartnerStorySection and GalleryOffers.
Partner workspace: PartnerStoryManager, PartnerStoryEditor, OriginalHistoryForm, StoryMediaUploader, StoryReferenceManager, StoryTimelineEditor, StoryVersionHistory, StoryApprovalPanel and StoryPreview.
Use semantic links/buttons, visible focus styles, Escape handling for expanded views, responsive layouts and reduced-motion support.

## 9. Analytics
Track privacy-conscious impressions, overlay activations, partner-profile clicks, story engagement, enquiries, related trip clicks, promotion clicks and attributable completed bookings where verified. Do not equate an impression with a story interaction or booking.

## 10. Priority backlog
P0: audit authentication/partner/media foundations; create Gallery models; add rights and approvals; enforce partner permissions and public/private serializers; implement publication guard and backend tests; build public Gallery and accessible story cards; build partner submission and editorial publishing.
P1: AI-assisted story drafting with source/version tracking; partner profiles and approved extended histories; optional timelines; notifications.
P2: analytics dashboards, campaign collections, sponsored placements and additional languages.

## 11. Acceptance tests
- Only currently approved partners appear publicly.
- Gallery advertising approval does not imply booking approval.
- Every image can link to its own approved story.
- Hover, focus and touch reveal the same 30–60-word summary.
- Story selection opens the correct partner/story.
- Public APIs never expose private original history or internal references.
- Partner A cannot access or modify Partner B content.
- Missing, expired or withdrawn media permission blocks publication.
- Owner and editorial approvals refer to the current version.
- Material edits invalidate prior approvals.
- AI drafts remain unpublished and contain no unsupported invented facts.
- Suspension or partner ineligibility removes public visibility.
- Changes and publication actions are auditable.
- Responsive, keyboard and screen-reader tests pass.

## 12. Dependencies and compliance
Dependencies: authentication, partner verification, media storage, notification service and editorial role management. Obtain appropriate South African legal review covering POPIA, copyright/licensing, consent for identifiable people, advertising disclosures, partner agreements and retention of evidence.