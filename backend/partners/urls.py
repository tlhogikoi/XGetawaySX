from django.urls import path

from .views import (\n    PublicDestinationDetailView, PublicDestinationListView,\n    PublicExperienceCollectionDetailView, PublicExperienceCollectionListView,\n    PublicPartnerDetailView, PublicPartnerListView,\n)

urlpatterns = [
    path("", PublicPartnerListView.as_view(), name="public-partners"),\n    path("destinations/", PublicDestinationListView.as_view(), name="public-destinations"),\n    path("destinations/<slug:slug>/", PublicDestinationDetailView.as_view(), name="public-destination-detail"),\n    path("collections/", PublicExperienceCollectionListView.as_view(), name="public-experience-collections"),\n    path("collections/<slug:slug>/", PublicExperienceCollectionDetailView.as_view(), name="public-experience-collection-detail"),
    path("<slug:slug>/", PublicPartnerDetailView.as_view(), name="public-partner-detail"),
]
