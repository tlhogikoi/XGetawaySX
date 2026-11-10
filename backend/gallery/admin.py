from django.contrib import admin

from .models import GalleryMedia, GalleryStory


@admin.register(GalleryMedia)
class GalleryMediaAdmin(admin.ModelAdmin):
    list_display = ("title", "partner", "status", "rights_confirmed", "promotional_permission")
    list_filter = ("status", "rights_confirmed", "promotional_permission")
    search_fields = ("title", "partner__name", "rights_holder")


@admin.register(GalleryStory)
class GalleryStoryAdmin(admin.ModelAdmin):
    list_display = ("media", "status", "owner_approved_at", "editorial_approved_at", "published_at")
    list_filter = ("status", "owner_history_private")
    search_fields = ("media__title", "media__partner__name", "summary")
    readonly_fields = ("created_at", "updated_at")
