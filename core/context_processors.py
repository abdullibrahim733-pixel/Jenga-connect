from .models import Notification, Profile


def notification_context(request):
    if not request.user.is_authenticated:
        return {}

    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return {}

    unread_count = Notification.objects.filter(
        user=profile, is_read=False
    ).count()
    preview = (
        Notification.objects.filter(user=profile)
        .select_related("order")
        .order_by("-created_at")[:5]
    )
    return {
        "notification_unread_count": unread_count,
        "notifications_preview": preview,
    }
