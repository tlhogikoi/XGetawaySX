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
