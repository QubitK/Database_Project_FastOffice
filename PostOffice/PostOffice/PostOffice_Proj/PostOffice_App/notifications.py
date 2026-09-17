# PostOffice_App/notifications.py
from django.utils import timezone
from pymongo import MongoClient
from bson import ObjectId
from datetime import timedelta

# ============================
# MONGO: CENTRALIZED CONNECTION
# ============================
mongo_client = MongoClient("mongodb://localhost:27017")
mongo_db = mongo_client["postoffice"]
notifications_collection = mongo_db["notifications"]


def create_notification(notification_type, recipient_contact, subject, message, status="pending"):
    """Create a new notification in MongoDB."""
    try:
        notifications_collection.insert_one({
            "notification_type": notification_type,
            "recipient_contact": recipient_contact,
            "subject": subject,
            "message": message,
            "status": status,
            "is_read": False,
            "created_at": timezone.now(),
        })
    except Exception:
        pass


def get_user_notifications(user_email, max_age_minutes=3):
    """Retrieve recent notifications for a user."""
    cutoff_time = timezone.now() - timedelta(minutes=max_age_minutes)

    notifs = list(
        notifications_collection.find({
            "recipient_contact": user_email,
            "created_at": {"$gte": cutoff_time}
        }).sort("created_at", -1)
    )

    data = []
    for n in notifs:
        data.append({
            "id": str(n["_id"]),
            "message": n.get("message", ""),
            "is_read": n.get("is_read", False),
            "created_at": n["created_at"].strftime("%d/%m %H:%M")
        })
    return data


def mark_as_read(notif_id):
    """Mark a specific notification as read."""
    try:
        result = notifications_collection.update_one(
            {"_id": ObjectId(notif_id)},
            {"$set": {"is_read": True}}
        )
        return result.modified_count > 0
    except Exception:
        return False
