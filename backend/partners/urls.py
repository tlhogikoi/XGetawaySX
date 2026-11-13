from django.urls import path

from .views import (
    PublicDestinationDetailView, PublicDestinationListView,
    PublicExperienceCollectionDetailView, PublicExperienceCollectionListView,
    PublicPartnerDetailView, PublicPartnerListView,\n    CustomerEnquiryListCreateView, PartnerEnquiryRespondView,\n    PartnerIncomingEnquiryListView, TripPlanDetailView,\n    TripPlanItemCreateView, TripPlanItemDetailView, TripPlanListCreateView,
)

urlpatterns = [
    path("", PublicPartnerListView.as_view(), name="public-partners"),
    path("destinations/", PublicDestinationListView.as_view(), name="public-destinations"),
    path("destinations/<slug:slug>/", PublicDestinationDetailView.as_view(), name="public-destination-detail"),
    path("collections/", PublicExperienceCollectionListView.as_view(), name="public-experience-collections"),
    path("collections/<slug:slug>/", PublicExperienceCollectionDetailView.as_view(), name="public-experience-collection-detail"),
    path("trips/", TripPlanListCreateView.as_view(), name="trip-plan-list-create"),\n    path("trips/<int:pk>/", TripPlanDetailView.as_view(), name="trip-plan-detail"),\n    path("trips/<int:pk>/items/", TripPlanItemCreateView.as_view(), name="trip-plan-item-create"),\n    path("trips/<int:pk>/items/<int:item_id>/", TripPlanItemDetailView.as_view(), name="trip-plan-item-detail"),\n    path("enquiries/", CustomerEnquiryListCreateView.as_view(), name="customer-enquiry-list-create"),\n    path("partner/enquiries/", PartnerIncomingEnquiryListView.as_view(), name="partner-incoming-enquiries"),\n    path("partner/enquiries/<int:pk>/respond/", PartnerEnquiryRespondView.as_view(), name="partner-enquiry-respond"),\n    path("<slug:slug>/", PublicPartnerDetailView.as_view(), name="public-partner-detail"),
]
