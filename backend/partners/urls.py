from django.urls import path

from .views import PublicPartnerDetailView, PublicPartnerListView

urlpatterns = [
    path("", PublicPartnerListView.as_view(), name="public-partners"),
    path("<slug:slug>/", PublicPartnerDetailView.as_view(), name="public-partner-detail"),
]
