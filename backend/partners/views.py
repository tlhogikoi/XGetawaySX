from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from gallery.serializers import PublicGalleryStorySerializer
from gallery.views import PublicGalleryStoriesView
from .models import Partner
from .serializers import PublicPartnerSerializer


class PublicPartnerListView(ListAPIView):
    serializer_class = PublicPartnerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Partner.objects.filter(
            gallery_status=Partner.ApprovalStatus.APPROVED
        ).order_by("name")


class PublicPartnerDetailView(APIView):
    """Public profile with only Gallery-published stories and approved profile fields."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        partner = get_object_or_404(
            Partner.objects.filter(gallery_status=Partner.ApprovalStatus.APPROVED),
            slug=slug,
        )
        published_stories = PublicGalleryStoriesView().get_queryset().filter(
            media__partner=partner
        )
        return Response({
            **PublicPartnerSerializer(partner, context={"request": request}).data,
            "stories": PublicGalleryStorySerializer(
                published_stories, many=True, context={"request": request}
            ).data,
        })
