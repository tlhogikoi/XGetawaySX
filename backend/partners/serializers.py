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


from .models import PartnerEnquiry, TripPlan, TripPlanItem


class TripPlanItemSerializer(serializers.ModelSerializer):
    partner = PublicPartnerSerializer(read_only=True)

    class Meta:
        model = TripPlanItem
        fields = ("id", "partner", "note", "display_order", "added_at")
        read_only_fields = fields


class TripPlanSerializer(serializers.ModelSerializer):
    items = TripPlanItemSerializer(many=True, read_only=True)

    class Meta:
        model = TripPlan
        fields = ("id", "title", "notes", "start_date", "end_date", "items", "created_at", "updated_at")
        read_only_fields = ("id", "items", "created_at", "updated_at")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})
        return attrs


class TripPlanItemCreateSerializer(serializers.Serializer):
    partner_id = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate_partner_id(self, value):
        try:
            partner = Partner.objects.get(
                pk=value,
                gallery_status=Partner.ApprovalStatus.APPROVED,
                enquiry_status=Partner.ApprovalStatus.APPROVED,
            )
        except Partner.DoesNotExist:
            raise serializers.ValidationError("This partner is not currently available for trip planning.")
        return partner.pk


class PartnerEnquiryCreateSerializer(serializers.Serializer):
    partner_id = serializers.IntegerField()
    trip_plan_id = serializers.IntegerField(required=False, allow_null=True)
    message = serializers.CharField(min_length=10, max_length=5000)
    requested_start_date = serializers.DateField(required=False, allow_null=True)
    requested_end_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        start, end = attrs.get("requested_start_date"), attrs.get("requested_end_date")
        if start and end and end < start:
            raise serializers.ValidationError({"requested_end_date": "End date cannot be earlier than start date."})
        try:
            partner = Partner.objects.get(
                pk=attrs["partner_id"],
                gallery_status=Partner.ApprovalStatus.APPROVED,
                enquiry_status=Partner.ApprovalStatus.APPROVED,
            )
        except Partner.DoesNotExist:
            raise serializers.ValidationError({"partner_id": "This partner is not accepting enquiries."})
        attrs["partner"] = partner
        plan_id = attrs.get("trip_plan_id")
        if plan_id:
            try:
                plan = TripPlan.objects.get(pk=plan_id, owner=self.context["request"].user)
            except TripPlan.DoesNotExist:
                raise serializers.ValidationError({"trip_plan_id": "Trip plan not found."})
            if not plan.items.filter(partner=partner).exists():
                raise serializers.ValidationError({"trip_plan_id": "Add this partner to the trip plan before enquiring."})
            attrs["trip_plan"] = plan
        return attrs


class PartnerEnquirySerializer(serializers.ModelSerializer):
    partner = PublicPartnerSerializer(read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)

    class Meta:
        model = PartnerEnquiry
        fields = (
            "id", "partner", "trip_plan_id", "message", "requested_start_date",
            "requested_end_date", "status", "partner_response", "customer_email",
            "responded_at", "created_at", "updated_at",
        )
        read_only_fields = fields


class PartnerEnquiryResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(PartnerEnquiry.Status.ACCEPTED, PartnerEnquiry.Status.DECLINED))
    partner_response = serializers.CharField(min_length=5, max_length=5000)
