from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", include("health.urls")),
    path("api/v1/partners/", include("partners.urls")),
    path("api/v1/gallery/", include("gallery.urls")),
]
