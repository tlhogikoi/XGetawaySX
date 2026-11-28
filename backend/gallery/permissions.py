from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsPartnerOwnerOrEditorial(BasePermission):
    """Owners may manage their own submissions; staff may review editorially."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        if request.user and request.user.is_staff:
            return True
        partner = getattr(obj, "partner", None)
        if partner is None and hasattr(obj, "media"):
            partner = obj.media.partner
        return bool(partner and partner.owner_id == request.user.id)
