from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AccountTokenObtainPairView, CurrentAccountView, CustomerRegistrationView
from .privacy_urls import urlpatterns as privacy_urlpatterns

urlpatterns = [
    path("register/", CustomerRegistrationView.as_view(), name="customer-register"),
    path("token/", AccountTokenObtainPairView.as_view(), name="account-token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="account-token-refresh"),
    path("me/", CurrentAccountView.as_view(), name="current-account"),
    path("privacy-requests/", include(privacy_urlpatterns)),
]
