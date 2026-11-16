from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    AccountUserSerializer,
    CustomerRegistrationSerializer,
    XGetawayTokenObtainPairSerializer,
)


class CustomerRegistrationView(generics.CreateAPIView):
    serializer_class = CustomerRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AccountUserSerializer(user).data, status=status.HTTP_201_CREATED)


class AccountTokenObtainPairView(TokenObtainPairView):
    serializer_class = XGetawayTokenObtainPairSerializer
    permission_classes = [AllowAny]


class CurrentAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AccountUserSerializer(request.user).data)
