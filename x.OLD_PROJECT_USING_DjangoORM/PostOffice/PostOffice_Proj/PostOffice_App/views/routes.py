# ==========================================================
#  ROUTES
# ==========================================================
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json
from pyexpat.errors import messages
from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from ..models import Invoice, Route, User
from ..forms import InvoiceForm, RouteForm
from .decorators import role_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from ..notifications import create_notification

@login_required
def routes_list(request):
    routes_qs = Route.objects.select_related("driver", "vehicle").all()
    paginator = Paginator(routes_qs, 10)
    page_number = request.GET.get("page")
    routes_page = paginator.get_page(page_number)
    return render(request, "routes/list.html", {"routes": routes_page})


@login_required
@role_required(["admin"])
def routes_create(request):
    if request.method == "POST":
        form = RouteForm(request.POST)
        if form.is_valid():
            # Save the route and get the instance
            route = form.save()

            # Create notification for the admin who created it
            create_notification(
                notification_type="route_created",
                recipient_contact=request.user.email,  # Send to current admin
                subject="Route Created",
                message=f"Successfully created route: {route.origin_name} → {route.destination_name}",
                status="sent"
            )

            return redirect("routes_list")
    else:
        form = RouteForm()
    return render(request, "routes/create.html", {"form": form})


@login_required
@role_required(["admin"])
def routes_edit(request, route_id):
    route = get_object_or_404(Route, pk=route_id)
    if request.method == "POST":
        form = RouteForm(request.POST, instance=route)
        if form.is_valid():
            # Save the updated route
            form.save()

            # Create notification for the admin who edited it
            create_notification(
                notification_type="route_updated",
                recipient_contact=request.user.email,  # Send to current admin
                subject="Route Updated",
                message=f"Successfully updated route: {route.origin_name} → {route.destination_name}",
                status="sent"
            )

            return redirect("routes_list")
    else:
        form = RouteForm(instance=route)
    return render(request, "routes/edit.html", {"form": form, "route": route})


@login_required
@role_required(["admin"])
def routes_delete(request, route_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method for deletion.")

    route = get_object_or_404(Route, pk=route_id)
    # Store route info before deleting
    route_info = f"{route.origin_name} → {route.destination_name}"

    try:
        route.delete()

        # Create notification after successful deletion
        create_notification(
            notification_type="route_deleted",
            recipient_contact=request.user.email,  # Send to admin who deleted it
            subject="Route Deleted",
            message=f"Successfully deleted route: {route_info}",
            status="sent"
        )

        messages.success(request, "Route deleted successfully.")
    except Exception:
        messages.error(request, "An error occurred while deleting the route.")

    return redirect("routes_list")


# ==========================================================
# IMPORT/EXPORT JSON
# ==========================================================

@login_required
@role_required(["admin", "manager"])
def routes_import_json(request):
    if request.method == "POST":
        file = request.FILES.get("file")

        if not file:
            messages.error(request, "You must upload a JSON file.")
            return redirect("routes_import_json")

        try:
            data = json.load(file)
        except Exception:
            messages.error(request, "Invalid JSON file.")
            return redirect("routes_import_json")

        if not isinstance(data, list):
            messages.error(request, "JSON must contain a list of routes.")
            return redirect("routes_import_json")

        count = 0

        for item in data:

            # Always remove id to avoid IntegrityError
            if "id" in item:
                del item["id"]

            # Create the route safely
            Route.objects.create(
                description=item.get("description", ""),
                delivery_status=item.get("delivery_status", ""),

                vehicle_id=item.get("vehicle_id"),
                driver_id=item.get("driver_id"),

                origin_name=item.get("origin_name", ""),
                origin_address=item.get("origin_address", ""),
                origin_contact=item.get("origin_contact", ""),

                destination_name=item.get("destination_name", ""),
                destination_address=item.get("destination_address", ""),
                destination_contact=item.get("destination_contact", ""),

                delivery_date=item.get("delivery_date"),
                delivery_start_time=item.get("delivery_start_time"),
                delivery_end_time=item.get("delivery_end_time"),

                kms_travelled=item.get("kms_travelled", 0),
                expected_duration=item.get("expected_duration"),

                driver_notes=item.get("driver_notes", "")
            )

            count += 1

        # Create notification for the user who imported
        create_notification(
            notification_type="routes_imported",
            recipient_contact=request.user.email,
            subject="Routes Imported",
            message=f"Successfully imported {count} routes from JSON",
            status="sent"
        )

        messages.success(request, f"Imported {count} routes successfully.")
        return redirect("routes_list")

    return render(request, "routes/import.html")


@login_required
@role_required(["admin", "manager"])
def routes_export_json(request):
    routes = list(
        Route.objects.all().values(
            "id",
            "description",
            "delivery_status",
            "vehicle_id",
            "driver_id",
            "origin_name",
            "origin_address",
            "origin_contact",
            "destination_name",
            "destination_address",
            "destination_contact",
            "delivery_date",
            "delivery_start_time",
            "delivery_end_time",
            "kms_travelled",
            "expected_duration",
            "driver_notes",
        )
    )

    for r in routes:
        if isinstance(r["delivery_date"], date):
            r["delivery_date"] = r["delivery_date"].strftime("%Y-%m-%d")

        if isinstance(r["delivery_start_time"], time):
            r["delivery_start_time"] = r["delivery_start_time"].strftime("%H:%M:%S")

        if isinstance(r["delivery_end_time"], time):
            r["delivery_end_time"] = r["delivery_end_time"].strftime("%H:%M:%S")

        if isinstance(r["expected_duration"], timedelta):
            total_seconds = int(r["expected_duration"].total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            r["expected_duration"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    json_data = json.dumps(routes, indent=4)
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="routes_export.json"'

    # Create notification for the user who exported
    create_notification(
        notification_type="routes_exported",
        recipient_contact=request.user.email,
        subject="Routes Exported",
        message=f"Successfully exported {len(routes)} routes to JSON",
        status="sent"
    )

    return response


# ==========================================================
# EXPORT CSV
# ==========================================================

@login_required
@role_required(["admin", "manager"])
def routes_export_csv(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM export_routes_csv();")
        rows = cursor.fetchall()

    header = (
        "id,description,delivery_status,"
        "vehicle_id,driver_id,"
        "origin_name,origin_address,origin_contact,"
        "destination_name,destination_address,destination_contact,"
        "delivery_date,delivery_start_time,delivery_end_time,"
        "kms_travelled,expected_duration,driver_notes\n"
    )
    csv_data = header + "\n".join(r[0] for r in rows)

    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="routes_export.csv"'

    # Create notification for the user who exported
    create_notification(
        notification_type="routes_exported_csv",
        recipient_contact=request.user.email,
        subject="Routes Exported",
        message=f"Successfully exported {len(rows)} routes to CSV",
        status="sent"
    )

    return response