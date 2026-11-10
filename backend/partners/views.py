from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from .models import Partner
from .serializers import PublicPartnerSerializer


class PublicPartnerListView(ListAPIView):
    serializer_class = PublicPartnerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Partner.objects.filter(
            gallery_status=Partner.ApprovalStatus.APPROVED
        ).order_by("name")
