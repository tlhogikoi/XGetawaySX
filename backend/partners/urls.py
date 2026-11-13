from django.urls import path

from .views import (
    PublicDestinationDetailView, PublicDestinationListView,
    PublicExperienceCollectionDetailView, PublicExperienceCollectionListView,
    PublicPartnerDetailView, PublicPartnerListView,
    CustomerEnquiryListCreateView, PartnerEnquiryRespondView,
    PartnerIncomingEnquiryListView, TripPlanDetailView,
    TripPlanItemCreateView, TripPlanItemDetailView, TripPlanListCreateView,
)

urlpatterns = [
    path("", PublicPartnerListView.as_view(), name="public-partners"),
    path("destinations/", PublicDestinationListView.as_view(), name="public-destinations"),
    path("destinations/<slug:slug>/", PublicDestinationDetailView.as_view(), name="public-destination-detail"),
    path("collections/", PublicExperienceCollectionListView.as_view(), name="public-experience-collections"),
    path("collections/<slug:slug>/", PublicExperienceCollectionDetailView.as_view(), name="public-experience-collection-detail"),
    path("trips/", TripPlanListCreateView.as_view(), name="trip-plan-list-create"),
    path("trips/<int:pk>/", TripPlanDetailView.as_view(), name="trip-plan-detail"),
    path("trips/<int:pk>/items/", TripPlanItemCreateView.as_view(), name="trip-plan-item-create"),
    path("trips/<int:pk>/items/<int:item_id>/", TripPlanItemDetailView.as_view(), name="trip-plan-item-detail"),
    path("enquiries/", CustomerEnquiryListCreateView.as_view(), name="customer-enquiry-list-create"),
    path("partner/enquiries/", PartnerIncomingEnquiryListView.as_view(), name="partner-incoming-enquiries"),
    path("partner/enquiries/<int:pk>/respond/", PartnerEnquiryRespondView.as_view(), name="partner-enquiry-respond"),
    path("<slug:slug>/", PublicPartnerDetailView.as_view(), name="public-partner-detail"),
]
