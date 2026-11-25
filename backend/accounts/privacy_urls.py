from django.urls import path
from .privacy_views import PrivacyRequestDetailView, PrivacyRequestListCreateView

urlpatterns = [
    path("", PrivacyRequestListCreateView.as_view(), name="privacy-request-list-create"),
    path("<uuid:reference>/", PrivacyRequestDetailView.as_view(), name="privacy-request-detail"),
]
