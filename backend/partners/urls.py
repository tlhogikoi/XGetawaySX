from django.urls import path

from .views import PublicPartnerListView

urlpatterns = [
    path("", PublicPartnerListView.as_view(), name="public-partners"),
]
