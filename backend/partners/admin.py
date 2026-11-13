from django.contrib import admin

from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "city", "gallery_status", "enquiry_status", "booking_status")
    list_filter = ("category", "gallery_status", "enquiry_status", "booking_status", "province")
    search_fields = ("name", "city", "owner__email")
    readonly_fields = ("created_at", "updated_at")


from .models import DestinationPage, ExperienceCollection


@admin.register(DestinationPage)
class DestinationPageAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "province", "country", "is_published", "display_order")
    list_filter = ("is_published", "province", "country")
    search_fields = ("name", "slug", "city", "province")
    filter_horizontal = ("partners",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ExperienceCollection)
class ExperienceCollectionAdmin(admin.ModelAdmin):
    list_display = ("title", "destination", "is_published", "display_order")
    list_filter = ("is_published", "destination")
    search_fields = ("title", "slug", "summary")
    filter_horizontal = ("partners",)
    prepopulated_fields = {"slug": ("title",)}


from .models import PartnerEnquiry, TripPlan, TripPlanItem


class TripPlanItemInline(admin.TabularInline):
    model = TripPlanItem
    extra = 0
    autocomplete_fields = ("partner",)


@admin.register(TripPlan)
class TripPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "start_date", "end_date", "updated_at")
    search_fields = ("title", "owner__email")
    list_filter = ("start_date", "end_date")
    inlines = (TripPlanItemInline,)


@admin.register(PartnerEnquiry)
class PartnerEnquiryAdmin(admin.ModelAdmin):
    list_display = ("id", "partner", "customer", "status", "created_at", "responded_at")
    list_filter = ("status", "created_at")
    search_fields = ("partner__name", "customer__email", "message")
    readonly_fields = ("created_at", "updated_at", "responded_at")

from .models import PartnerAvailability, ReservationRequest, PartnerFinancialSettings, ReservationPayment, PartnerCommissionLedger


@admin.register(PartnerAvailability)
class PartnerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("partner", "date", "capacity", "booked_count", "is_open", "price_per_guest", "currency")
    list_filter = ("is_open", "currency", "date")
    search_fields = ("partner__name",)


@admin.register(ReservationRequest)
class ReservationRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "booking_reference", "partner", "customer", "start_date", "end_date", "status", "guests")
    list_filter = ("status", "start_date", "created_at")
    search_fields = ("booking_reference", "partner__name", "customer__email")
    readonly_fields = ("booking_reference", "created_at", "updated_at", "responded_at")


@admin.register(PartnerFinancialSettings)
class PartnerFinancialSettingsAdmin(admin.ModelAdmin):
    list_display = ("partner", "deposit_type", "deposit_value", "commission_rate", "currency", "updated_at")
    list_filter = ("deposit_type", "currency")
    search_fields = ("partner__name",)


@admin.register(ReservationPayment)
class ReservationPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "reservation", "partner", "customer", "kind", "status", "amount", "currency", "provider")
    list_filter = ("status", "kind", "provider", "currency")
    search_fields = ("provider_reference", "reservation__booking_reference", "partner__name", "customer__email")
    readonly_fields = ("created_at", "updated_at", "captured_at")


@admin.register(PartnerCommissionLedger)
class PartnerCommissionLedgerAdmin(admin.ModelAdmin):
    list_display = ("payment", "partner", "gross_amount", "commission_rate", "commission_amount", "partner_net_amount", "status")
    list_filter = ("status", "created_at")
    search_fields = ("partner__name", "payment__provider_reference")
    readonly_fields = ("created_at",)

