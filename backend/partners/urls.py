from django.urls import path

from .views import (
    PublicDestinationDetailView, PublicDestinationListView,
    PublicExperienceCollectionDetailView, PublicExperienceCollectionListView,
    PublicPartnerDetailView, PublicPartnerListView,
)

urlpatterns = [
    path("", PublicPartnerListView.as_view(), name="public-partners"),
    path("destinations/", PublicDestinationListView.as_view(), name="public-destinations"),
    path("destinations/<slug:slug>/", PublicDestinationDetailView.as_view(), name="public-destination-detail"),
    path("collections/", PublicExperienceCollectionListView.as_view(), name="public-experience-collections"),
    path("collections/<slug:slug>/", PublicExperienceCollectionDetailView.as_view(), name="public-experience-collection-detail"),
    path("<slug:slug>/", PublicPartnerDetailView.as_view(), name="public-partner-detail"),
]
