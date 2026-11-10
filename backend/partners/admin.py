from django.contrib import admin

from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "city", "gallery_status", "enquiry_status", "booking_status")
    list_filter = ("category", "gallery_status", "enquiry_status", "booking_status", "province")
    search_fields = ("name", "city", "owner__email")
    readonly_fields = ("created_at", "updated_at")
