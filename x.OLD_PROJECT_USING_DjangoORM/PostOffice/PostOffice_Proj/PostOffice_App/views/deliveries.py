# ==========================================================
#  DELIVERIES
# ==========================================================
from datetime import datetime
from decimal import Decimal
import json
from pyexpat.errors import messages
from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from ..models import Delivery, Invoice, User
from ..forms import DeliveryForm, DeliveryImportForm, InvoiceForm
from .decorators import role_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from ..notifications import create_notification

@login_required
@role_required(["driver", "admin", "client", "staff", "manager"])
def deliveries_list(request):
    role = request.user.role
    if role in {"admin", "manager", "staff"}:
        deliveries_qs = Delivery.objects.select_related("driver", "client", "route").all()
    elif role == "driver":
        employee = getattr(request.user, "employee", None)
        deliveries_qs = Delivery.objects.filter(driver=employee) if employee else Delivery.objects.none()
    else:  # client
        deliveries_qs = Delivery.objects.filter(client=request.user)
    paginator = Paginator(deliveries_qs, 10)
    page_number = request.GET.get("page")
    deliveries_page = paginator.get_page(page_number)
    return render(request, "deliveries/list.html", {"deliveries": deliveries_page})


@login_required
def deliveries_detail(request, delivery_id):
    delivery = get_object_or_404(Delivery, pk=delivery_id)
    return render(request, "deliveries/detail.html", {"delivery": delivery})


@login_required
@role_required(["admin", "staff"])
def deliveries_create(request):
    if request.method == "POST":
        form = DeliveryForm(request.POST)
        if form.is_valid():
            # Save the delivery and get the instance
            new_delivery = form.save()

            # Notification for the recipient (client/customer) - existing logic
            recipient = None
            if new_delivery.client and new_delivery.client.contact:
                recipient = new_delivery.client.contact
            elif new_delivery.recipient_email:
                recipient = new_delivery.recipient_email

            if recipient:
                create_notification(
                    notification_type="delivery_created",
                    recipient_contact=recipient,
                    subject="New delivery registered",
                    message=f"Delivery {new_delivery.tracking_number} has been registered.",
                )

            # Notification for the admin/staff who created it
            create_notification(
                notification_type="delivery_created_admin",
                recipient_contact=request.user.email,  # Send to current admin/staff
                subject="Delivery Created",
                message=f"Successfully created delivery: {new_delivery.tracking_number} ({new_delivery.recipient_name})",
                status="sent"
            )

            return redirect("deliveries_list")
    else:
        form = DeliveryForm()
    return render(request, "deliveries/create.html", {"form": form})


@login_required
@role_required(["admin", "staff"])
def deliveries_edit(request, delivery_id):
    delivery = get_object_or_404(Delivery, pk=delivery_id)
    if request.method == "POST":
        form = DeliveryForm(request.POST, instance=delivery)
        if form.is_valid():
            # Save the updated delivery
            form.save()

            # Create notification for the admin/staff who edited it
            create_notification(
                notification_type="delivery_updated",
                recipient_contact=request.user.email,  # Send to current admin/staff
                subject="Delivery Updated",
                message=f"Successfully updated delivery: {delivery.tracking_number} ({delivery.recipient_name})",
                status="sent"
            )

            return redirect("deliveries_list")
    else:
        form = DeliveryForm(instance=delivery)
    return render(request, "deliveries/edit.html", {"form": form, "delivery": delivery})


@login_required
@role_required(["admin"])
def deliveries_delete(request, delivery_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method for deletion.")

    delivery = get_object_or_404(Delivery, pk=delivery_id)
    # Store delivery info before deleting
    delivery_info = f"{delivery.tracking_number} ({delivery.recipient_name})"

    try:
        delivery.delete()

        # Create notification after successful deletion
        create_notification(
            notification_type="delivery_deleted",
            recipient_contact=request.user.email,  # Send to admin who deleted it
            subject="Delivery Deleted",
            message=f"Successfully deleted delivery: {delivery_info}",
            status="sent"
        )

        messages.success(request, "Delivery deleted successfully.")
    except Exception:
        messages.error(request, "An error occurred while deleting the delivery.")

    return redirect("deliveries_list")


# ==========================================================
# IMPORT/EXPORT JSON
# ==========================================================

@login_required
@role_required(["admin", "manager"])
def deliveries_export_json(request):
    deliveries = Delivery.objects.all().values()

    cleaned = []
    for d in deliveries:
        row = {}
        for key, value in d.items():
            if hasattr(value, "isoformat"):
                row[key] = value.isoformat()
            else:
                row[key] = value
        cleaned.append(row)

    json_data = json.dumps(cleaned, indent=4)
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = "attachment; filename=deliveries.json"

    # Create notification for the user who exported
    create_notification(
        notification_type="deliveries_exported",
        recipient_contact=request.user.email,
        subject="Deliveries Exported",
        message=f"Successfully exported {len(cleaned)} deliveries to JSON",
        status="sent"
    )

    return response


@login_required
@role_required(["admin", "manager"])
def deliveries_import_json(request):
    if request.method == "POST":
        form = DeliveryImportForm(request.POST, request.FILES)

        if form.is_valid():
            file = request.FILES["file"]
            data = json.load(file)

            count = 0

            for item in data:

                # Debug print – REMOVE AFTER TESTING
                print("IMPORT ITEM BEFORE CLEAN:", item)

                # Remove ANY key that looks like an id
                for key in list(item.keys()):
                    if key.lower() == "id":
                        item.pop(key)

                # Debug print – REMOVE AFTER TESTING
                print("IMPORT ITEM AFTER CLEAN:", item)

                Delivery.objects.create(
                    tracking_number=item.get("tracking_number"),
                    description=item.get("description"),
                    sender_name=item.get("sender_name"),
                    sender_address=item.get("sender_address"),
                    sender_phone=item.get("sender_phone"),
                    sender_email=item.get("sender_email"),
                    recipient_name=item.get("recipient_name"),
                    recipient_address=item.get("recipient_address"),
                    recipient_phone=item.get("recipient_phone"),
                    recipient_email=item.get("recipient_email"),
                    item_type=item.get("item_type"),
                    weight=item.get("weight"),
                    dimensions=item.get("dimensions"),
                    status=item.get("status"),
                    priority=item.get("priority"),
                    destination=item.get("destination"),
                    delivery_date=item.get("delivery_date"),

                    # Foreign keys
                    driver_id=item.get("driver_id"),
                    client_id=item.get("client_id"),
                    route_id=item.get("route_id"),
                    invoice_id=item.get("invoice_id"),
                )

                count += 1

            # Create notification for the user who imported
            create_notification(
                notification_type="deliveries_imported",
                recipient_contact=request.user.email,
                subject="Deliveries Imported",
                message=f"Successfully imported {count} deliveries from JSON",
                status="sent"
            )

            messages.success(request, f"Imported {count} deliveries successfully.")
            return redirect("deliveries_list")

    else:
        form = DeliveryImportForm()

    return render(request, "deliveries/import.html", {"form": form})


# ==========================================================
# EXPORT CSV
# ==========================================================


@login_required
@role_required(["admin", "manager"])
def deliveries_export_csv(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM export_deliveries_csv();")
        rows = cursor.fetchall()

    header = (
        "id,tracking_number,description,"
        "sender_name,sender_address,sender_phone,sender_email,"
        "recipient_name,recipient_address,recipient_phone,recipient_email,"
        "item_type,weight,dimensions,status,priority,"
        "registered_at,updated_at,in_transition,destination,delivery_date,"
        "driver_id,invoice_id,route_id,client_id\n"
    )
    csv_data = header + "\n".join(r[0] for r in rows)

    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="deliveries_export.csv"'

    # Create notification for the user who exported
    create_notification(
        notification_type="deliveries_exported_csv",
        recipient_contact=request.user.email,
        subject="Deliveries Exported",
        message=f"Successfully exported {len(rows)} deliveries to CSV",
        status="sent"
    )

    return response