from django.contrib import admin

from .models import GalleryAuditEvent, GalleryHistoryPublicationConsent, GalleryMedia, GalleryStory, GalleryStoryRevision


@admin.register(GalleryMedia)
class GalleryMediaAdmin(admin.ModelAdmin):
    list_display = ("title", "partner", "status", "rights_confirmed", "promotional_permission")
    list_filter = ("status", "rights_confirmed", "promotional_permission")
    readonly_fields = tuple(field.name for field in GalleryMedia._meta.fields)
    search_fields = ("title", "partner__name", "rights_holder")


@admin.register(GalleryStory)
class GalleryStoryAdmin(admin.ModelAdmin):
    list_display = ("media", "status", "owner_approved_at", "editorial_approved_at", "published_at")
    list_filter = ("status", "owner_history_private")
    search_fields = ("media__title", "media__partner__name", "summary")
    readonly_fields = tuple(field.name for field in GalleryStory._meta.fields)



@admin.register(GalleryHistoryPublicationConsent)
class GalleryHistoryPublicationConsentAdmin(admin.ModelAdmin):
    list_display = ("story", "story_version", "granted_by", "granted_at", "revoked_at")
    readonly_fields = ("story", "story_version", "granted_by", "granted_at", "revoked_by", "revoked_at", "created_at", "updated_at")


@admin.register(GalleryStoryRevision)
class GalleryStoryRevisionAdmin(admin.ModelAdmin):
    list_display = ("story", "version", "changed_by", "change_reason", "created_at")
    readonly_fields = tuple(field.name for field in GalleryStoryRevision._meta.fields)


@admin.register(GalleryAuditEvent)
class GalleryAuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "partner", "actor", "created_at")
    readonly_fields = tuple(field.name for field in GalleryAuditEvent._meta.fields)
