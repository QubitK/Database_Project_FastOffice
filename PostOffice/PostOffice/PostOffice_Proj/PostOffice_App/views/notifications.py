# PostOffice_App/views/notifications.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

# Import helper functions from app-level notifications.py
from PostOffice_App.notifications import get_user_notifications, mark_as_read


@login_required
def get_notifications(request):
    """API endpoint to fetch user's recent notifications."""
    user_email = request.user.email
    data = get_user_notifications(user_email)
    return JsonResponse({"notifications": data})


@login_required
def mark_notification_read(request, notif_id):
    """API endpoint to mark a notification as read."""
    success = mark_as_read(notif_id)
    return JsonResponse({"status": "ok" if success else "error"})
