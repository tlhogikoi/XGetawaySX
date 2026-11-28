from django.conf import settings
from django.db import models


class ConsentPreference(models.Model):
    class Purpose(models.TextChoices):
        EMAIL = "marketing_email", "Marketing email"
        SMS = "marketing_sms", "Marketing SMS"
        WHATSAPP = "marketing_whatsapp", "Marketing WhatsApp"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consent_preferences")
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    enabled = models.BooleanField(default=False)
    policy_version = models.CharField(max_length=40, default="2026-11")
    source = models.CharField(max_length=40, default="privacy_centre")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="consent_updates")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "purpose"), name="unique_user_consent_purpose")]
        ordering = ("purpose",)

    def __str__(self):
        return f"{self.user.email} · {self.purpose} · {'on' if self.enabled else 'off'}"


class ConsentEvent(models.Model):
    preference = models.ForeignKey(ConsentPreference, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="consent_events")
    previous_value = models.BooleanField()
    new_value = models.BooleanField()
    purpose = models.CharField(max_length=32)
    policy_version = models.CharField(max_length=40)
    source = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
