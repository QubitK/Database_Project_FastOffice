# ==========================================================
#  VEHICLES
# ==========================================================
from datetime import date, datetime
from decimal import Decimal
import json
from pyexpat.errors import messages
from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from ..models import Invoice, User, Vehicle
from ..forms import InvoiceForm, VehicleForm, VehicleImportForm
from .decorators import role_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from ..notifications import create_notification

@login_required
@role_required(["admin", "manager"])
def vehicles_create(request):
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            # Save the vehicle and get the instance
            vehicle = form.save()

            # Create notification for the user who created it
            create_notification(
                notification_type="vehicle_created",
                recipient_contact=request.user.email,  # Send to current admin/manager
                subject="Vehicle Created",
                message=f"Successfully created vehicle: {vehicle.plate_number} ({vehicle.brand} {vehicle.model})",
                status="sent"
            )

            return redirect("vehicles_list")
    else:
        form = VehicleForm()
    return render(request, "vehicles/create.html", {"form": form})


@login_required
@role_required(["admin", "manager", "staff"])
def vehicles_list(request):
    vehicles_qs = Vehicle.objects.all()
    paginator = Paginator(vehicles_qs, 10)
    page_number = request.GET.get("page")
    vehicles_page = paginator.get_page(page_number)
    return render(request, "vehicles/list.html", {"vehicles": vehicles_page})


@login_required
@role_required(["admin", "manager"])
def vehicles_edit(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    if request.method == "POST":
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            # Save the updated vehicle
            form.save()

            # Create notification for the user who edited it
            create_notification(
                notification_type="vehicle_updated",
                recipient_contact=request.user.email,  # Send to current admin/manager
                subject="Vehicle Updated",
                message=f"Successfully updated vehicle: {vehicle.plate_number} ({vehicle.brand} {vehicle.model})",
                status="sent"
            )

            return redirect("vehicles_list")
    else:
        form = VehicleForm(instance=vehicle)
    return render(
        request,
        "vehicles/edit.html",
        {"vehicle": vehicle, "vehicle_id": vehicle_id, "form": form},
    )


@login_required
@role_required(["admin"])
def vehicles_delete(request, vehicle_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method for deletion.")

    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    # Store vehicle info before deleting
    vehicle_info = f"{vehicle.plate_number} ({vehicle.brand} {vehicle.model})"

    try:
        vehicle.delete()

        # Create notification after successful deletion
        create_notification(
            notification_type="vehicle_deleted",
            recipient_contact=request.user.email,  # Send to admin who deleted it
            subject="Vehicle Deleted",
            message=f"Successfully deleted vehicle: {vehicle_info}",
            status="sent"
        )

        messages.success(request, "Vehicle deleted successfully.")
    except Exception:
        messages.error(request, "An error occurred while deleting the vehicle.")

    return redirect("vehicles_list")



# ==========================================================
# IMPORT/EXPORT JSON
# ==========================================================

@login_required
@role_required(["admin", "manager", "staff"])
def vehicles_export_json(request):
    vehicles = list(Vehicle.objects.all().values())
    cleaned = []
    for v in vehicles:
        v = dict(v)
        lm = v.get("last_maintenance_date")
        if isinstance(lm, (date, datetime)):
            v["last_maintenance_date"] = lm.isoformat()
        cleaned.append(v)

    json_data = json.dumps(cleaned, indent=4)
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="vehicles_export.json"'

    # Create notification for the user who exported
    create_notification(
        notification_type="vehicles_exported",
        recipient_contact=request.user.email,
        subject="Vehicles Exported",
        message=f"Successfully exported {len(cleaned)} vehicles to JSON",
        status="sent"
    )

    return response


@login_required
@role_required(["admin", "manager"])
def vehicles_import_json(request):
    if request.method == "POST":
        form = VehicleImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]

            try:
                data = json.load(file)
            except Exception:
                messages.error(request, "Invalid JSON file.")
                return redirect("vehicles_import_json")

            if not isinstance(data, list):
                messages.error(request, "JSON must contain a list of vehicles.")
                return redirect("vehicles_import_json")

            count = 0

            for item in data:
                if not isinstance(item, dict):
                    continue

                # 🔥 REMOVE ID ALWAYS — IMPORTER WILL BREAK WITHOUT THIS
                if "id" in item:
                    del item["id"]

                Vehicle.objects.create(
                    vehicle_type=item.get("vehicle_type"),
                    plate_number=item.get("plate_number"),
                    capacity=item.get("capacity"),
                    brand=item.get("brand"),
                    model=item.get("model"),
                    vehicle_status=item.get("vehicle_status"),
                    year=item.get("year"),
                    fuel_type=item.get("fuel_type"),
                    last_maintenance_date=item.get("last_maintenance_date"),
                )
                count += 1

            # Create notification for the user who imported
            create_notification(
                notification_type="vehicles_imported",
                recipient_contact=request.user.email,
                subject="Vehicles Imported",
                message=f"Successfully imported {count} vehicles from JSON",
                status="sent"
            )

            messages.success(request, f"Imported {count} vehicles successfully.")
            return redirect("vehicles_list")

    else:
        form = VehicleImportForm()

    return render(request, "vehicles/import.html", {"form": form})


# ==========================================================
# EXPORT CSV
# ==========================================================

@login_required
@role_required(["admin", "manager"])
def vehicles_export_csv(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM export_vehicles_csv();")
        rows = cursor.fetchall()

    header = "id,plate_number,model,brand,vehicle_status,year,fuel_type,capacity,last_maintenance_date\n"
    csv_data = header + "\n".join(r[0] for r in rows)

    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="vehicles_export.csv"'

    # Create notification for the user who exported
    create_notification(
        notification_type="vehicles_exported_csv",
        recipient_contact=request.user.email,
        subject="Vehicles Exported",
        message=f"Successfully exported {len(rows)} vehicles to CSV",
        status="sent"
    )

    return response