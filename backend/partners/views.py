from django.shortcuts import get_object_or_404
from django.db.models import Q
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
        # Keep the approval restriction as the base queryset for every public search.
        queryset = Partner.objects.filter(
            gallery_status=Partner.ApprovalStatus.APPROVED
        )
        params = self.request.query_params
        search = params.get("q", "").strip()[:100]
        category = params.get("category", "").strip()
        city = params.get("city", "").strip()[:100]
        province = params.get("province", "").strip()[:100]
        country = params.get("country", "").strip()[:100]

        valid_categories = {value for value, _label in Partner.Category.choices}
        if category in valid_categories:
            queryset = queryset.filter(category=category)
        if city:
            queryset = queryset.filter(city__icontains=city)
        if province:
            queryset = queryset.filter(province__icontains=province)
        if country:
            queryset = queryset.filter(country__icontains=country)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(city__icontains=search)
                | Q(province__icontains=search)
            )
        return queryset.order_by("name")


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


from rest_framework.generics import RetrieveAPIView
from .models import DestinationPage, ExperienceCollection
from .serializers import PublicDestinationSerializer, PublicExperienceCollectionSerializer


class PublicDestinationListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicDestinationSerializer

    def get_queryset(self):
        return DestinationPage.objects.filter(is_published=True).prefetch_related(
            "partners", "collections"
        ).order_by("display_order", "name")


class PublicDestinationDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicDestinationSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return DestinationPage.objects.filter(is_published=True).prefetch_related(
            "partners", "collections"
        )


class PublicExperienceCollectionListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicExperienceCollectionSerializer

    def get_queryset(self):
        queryset = ExperienceCollection.objects.filter(is_published=True).select_related(
            "destination"
        ).prefetch_related("partners")
        destination = self.request.query_params.get("destination", "").strip()[:180]
        if destination:
            queryset = queryset.filter(destination__slug=destination, destination__is_published=True)
        return queryset.order_by("display_order", "title")


class PublicExperienceCollectionDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicExperienceCollectionSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return ExperienceCollection.objects.filter(is_published=True).select_related(
            "destination"
        ).prefetch_related("partners")
