from django.contrib import admin
from .privacy_models import PrivacyRequest, PrivacyRequestEvent


class PrivacyRequestEventInline(admin.TabularInline):
    model = PrivacyRequestEvent
    extra = 0
    can_delete = False
    readonly_fields = ("actor", "from_status", "to_status", "note", "created_at")


@admin.register(PrivacyRequest)
class PrivacyRequestAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "request_type", "status", "identity_verified", "created_at")
    list_filter = ("request_type", "status", "identity_verified")
    search_fields = ("reference", "user__email")
    readonly_fields = ("reference", "created_at", "updated_at", "closed_at")
    inlines = (PrivacyRequestEventInline,)
