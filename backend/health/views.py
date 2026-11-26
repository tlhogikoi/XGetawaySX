from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    return JsonResponse({
        "status": "ok",
        "service": "xgetawaysx-api",
        "version": "v1",
    })


@require_GET
def readiness_check(request):
    """Verify the application can execute a lightweight database query."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({
            "status": "not_ready",
            "database": "unavailable",
        }, status=503)

    return JsonResponse({
        "status": "ready",
        "database": "connected",
    })
