from django.urls import path

from .views import (
    GalleryMediaCreateView,
    GalleryMediaEditorialApprovalView,
    GalleryStoryCreateView,
    GalleryStoryEditorialApprovalView,
    GalleryStoryOwnerApprovalView,
    GalleryStoryOwnerDraftListView,
    GalleryStoryDraftUpdateView,
    GalleryStoryRevisionListView,
    GalleryAuditEventListView,
    PublicGalleryStoriesView,
)

urlpatterns = [
    path("stories/", PublicGalleryStoriesView.as_view(), name="gallery-public-stories"),
    path("stories/drafts/", GalleryStoryOwnerDraftListView.as_view(), name="gallery-story-drafts"),
    path("stories/<int:pk>/draft/", GalleryStoryDraftUpdateView.as_view(), name="gallery-story-draft-update"),
    path("stories/<int:pk>/revisions/", GalleryStoryRevisionListView.as_view(), name="gallery-story-revisions"),
    path("audit/", GalleryAuditEventListView.as_view(), name="gallery-audit-events"),
    path("stories/create/", GalleryStoryCreateView.as_view(), name="gallery-story-create"),
    path("stories/<int:pk>/owner-approve/", GalleryStoryOwnerApprovalView.as_view(), name="gallery-story-owner-approve"),
    path("stories/<int:pk>/editorial-approve/", GalleryStoryEditorialApprovalView.as_view(), name="gallery-story-editorial-approve"),
    path("media/create/", GalleryMediaCreateView.as_view(), name="gallery-media-create"),
    path("media/<int:pk>/editorial-approve/", GalleryMediaEditorialApprovalView.as_view(), name="gallery-media-editorial-approve"),
]
