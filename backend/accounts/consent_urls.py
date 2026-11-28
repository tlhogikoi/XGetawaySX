from django.urls import path

from .consent_views import ConsentPreferenceView

urlpatterns = [
    path("", ConsentPreferenceView.as_view(), name="consent-preferences"),
]
