from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AccountTokenObtainPairView, CurrentAccountView, CustomerRegistrationView

urlpatterns = [
    path("register/", CustomerRegistrationView.as_view(), name="customer-register"),
    path("token/", AccountTokenObtainPairView.as_view(), name="account-token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="account-token-refresh"),
    path("me/", CurrentAccountView.as_view(), name="current-account"),
]
