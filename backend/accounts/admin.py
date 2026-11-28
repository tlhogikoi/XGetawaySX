from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "role", "is_staff")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
    search_fields = ("email", "first_name", "last_name")


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


from .consent_models import ConsentEvent, ConsentPreference


class ConsentEventInline(admin.TabularInline):
    model = ConsentEvent
    extra = 0
    can_delete = False
    readonly_fields = ("actor", "previous_value", "new_value", "purpose", "policy_version", "source", "created_at")


@admin.register(ConsentPreference)
class ConsentPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "enabled", "policy_version", "source", "updated_at")
    list_filter = ("purpose", "enabled", "source")
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (ConsentEventInline,)
