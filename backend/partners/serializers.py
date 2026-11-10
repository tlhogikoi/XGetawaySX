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
