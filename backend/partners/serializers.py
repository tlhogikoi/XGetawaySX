from rest_framework import serializers

from .models import Partner


class PublicPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = (
            "name",
            "slug",
            "category",
            "description",
            "city",
            "province",
            "country",
            "website_url",
        )
        read_only_fields = fields


from .models import DestinationPage, ExperienceCollection


class PublicDestinationSerializer(serializers.ModelSerializer):
    partners = serializers.SerializerMethodField()
    collections = serializers.SerializerMethodField()

    class Meta:
        model = DestinationPage
        fields = (
            "name", "slug", "introduction", "description", "city", "province",
            "country", "partners", "collections",
        )
        read_only_fields = fields

    def get_partners(self, obj):
        approved = obj.partners.filter(gallery_status=Partner.ApprovalStatus.APPROVED).order_by("name")
        return PublicPartnerSerializer(approved, many=True, context=self.context).data

    def get_collections(self, obj):
        items = obj.collections.filter(is_published=True).order_by("display_order", "title")
        return PublicExperienceCollectionSummarySerializer(items, many=True, context=self.context).data


class PublicExperienceCollectionSummarySerializer(serializers.ModelSerializer):
    destination_slug = serializers.SlugField(source="destination.slug", read_only=True, allow_null=True)

    class Meta:
        model = ExperienceCollection
        fields = ("title", "slug", "summary", "destination_slug")
        read_only_fields = fields


class PublicExperienceCollectionSerializer(serializers.ModelSerializer):
    destination_slug = serializers.SlugField(source="destination.slug", read_only=True, allow_null=True)
    partners = serializers.SerializerMethodField()

    class Meta:
        model = ExperienceCollection
        fields = ("title", "slug", "summary", "description", "destination_slug", "partners")
        read_only_fields = fields

    def get_partners(self, obj):
        approved = obj.partners.filter(gallery_status=Partner.ApprovalStatus.APPROVED).order_by("name")
        return PublicPartnerSerializer(approved, many=True, context=self.context).data
