# ==========================================================
#  WAREHOUSES
# ==========================================================
from datetime import datetime, time
from decimal import Decimal
import json
from pyexpat.errors import messages
from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest

from ..forms import WarehouseForm

from ..models import Warehouse
from ..forms import WarehouseImportForm
from .decorators import role_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from ..notifications import create_notification

@login_required
@role_required(["admin"])
def warehouses_list(request):
    warehouses_qs = Warehouse.objects.all()
    paginator = Paginator(warehouses_qs, 10)
    page_number = request.GET.get("page")
    warehouses_page = paginator.get_page(page_number)
    return render(request, "warehouses/list.html", {"warehouses": warehouses_page})


@login_required
@role_required(["admin"])
def warehouses_create(request):
    if request.method == "POST":
        form = WarehouseForm(request.POST)
        if form.is_valid():
            # Save the warehouse and get the instance
            warehouse = form.save()

            # Create notification for the admin who created it
            create_notification(
                notification_type="warehouse_created",
                recipient_contact=request.user.email,  # Send to current admin
                subject="Warehouse Created",
                message=f"Successfully created warehouse: {warehouse.name}",
                status="sent"
            )

            return redirect("warehouses_list")
    else:
        form = WarehouseForm()
    return render(request, "warehouses/create.html", {"form": form})


@login_required
@role_required(["admin", "staff"])
def warehouses_edit(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
    if request.method == "POST":
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            # Save the updated warehouse
            form.save()

            # Create notification for the user who edited it
            create_notification(
                notification_type="warehouse_updated",
                recipient_contact=request.user.email,  # Send to current user (admin/staff)
                subject="Warehouse Updated",
                message=f"Successfully updated warehouse: {warehouse.name}",
                status="sent"
            )

            messages.success(request, "Warehouse updated successfully.")
            return redirect("warehouses_list")
    else:
        form = WarehouseForm(instance=warehouse)
    return render(
        request,
        "warehouses/edit.html",
        {"form": form, "warehouse_id": warehouse_id},
    )


@login_required
@role_required(["admin"])
def warehouses_delete(request, warehouse_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method for deletion.")

    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
    # Store the warehouse name before deleting
    warehouse_name = warehouse.name

    try:
        warehouse.delete()

        # Create notification after successful deletion
        create_notification(
            notification_type="warehouse_deleted",
            recipient_contact=request.user.email,  # Send to admin who deleted it
            subject="Warehouse Deleted",
            message=f"Successfully deleted warehouse: {warehouse_name}",
            status="sent"
        )

        messages.success(request, "Warehouse deleted successfully.")
    except Exception:
        messages.error(request, "An error occurred while deleting the warehouse.")

    return redirect("warehouses_list")


# ==========================================================
# IMPORT/EXPORT JSON
# ==========================================================

@login_required
@role_required(["admin", "manager"])
def warehouses_export_json(request):
    warehouses = list(
        Warehouse.objects.all().values(
            "id",
            "name",
            "address",
            "contact",
            "po_schedule_open",
            "po_schedule_close",
            "maximum_storage_capacity",
        )
    )

    cleaned = []
    for w in warehouses:
        w = dict(w)
        for field in ("po_schedule_open", "po_schedule_close"):
            val = w.get(field)
            if isinstance(val, time):
                w[field] = val.strftime("%H:%M:%S")
        cleaned.append(w)

    json_data = json.dumps(cleaned, indent=4)
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="warehouses_export.json"'

    # Create notification for the user who exported
    create_notification(
        notification_type="warehouses_exported",
        recipient_contact=request.user.email,
        subject="Warehouses Exported",
        message=f"Successfully exported {len(cleaned)} warehouses to JSON",
        status="sent"
    )

    return response


@login_required
@role_required(["admin"])
def warehouses_import_json(request):
    if request.method == "POST":
        form = WarehouseImportForm(request.POST, request.FILES)

        if form.is_valid():
            file = request.FILES["file"]

            # Load JSON safely
            try:
                data = json.load(file)
            except Exception:
                messages.error(request, "Invalid JSON file.")
                return redirect("warehouses_import_json")

            if not isinstance(data, list):
                messages.error(request, "JSON must contain a list of warehouses.")
                return redirect("warehouses_import_json")

            count = 0

            for raw in data:
                if not isinstance(raw, dict):
                    continue

                item = dict(raw)  # isolate mutation

                # =====================================================
                # 1. STRIP ANY PRIMARY KEY FIELD (absolute protection)
                # =====================================================
                for key in list(item.keys()):
                    if "id" in key.lower():
                        item.pop(key, None)

                # =====================================================
                # 2. MAP BOTH IMPORT & EXPORT FIELD NAMES
                # =====================================================
                name = item.get("name")

                address = (
                    item.get("address")
                    or item.get("location")
                )

                contact = item.get("contact")

                po_open = item.get("po_schedule_open")
                po_close = item.get("po_schedule_close")

                max_capacity = (
                    item.get("maximum_storage_capacity")
                    or item.get("capacity")
                )

                # =====================================================
                # 3. VALIDATE required NOT NULL fields manually
                # =====================================================
                if not name or not address:
                    continue

                # =====================================================
                # 4. CREATE SAFE NEW WAREHOUSE ENTRY
                # =====================================================
                Warehouse.objects.create(
                    name=name,
                    address=address,
                    contact=contact,
                    po_schedule_open=po_open,
                    po_schedule_close=po_close,
                    maximum_storage_capacity=max_capacity,
                )

                count += 1

            # Create notification for the user who imported
            create_notification(
                notification_type="warehouses_imported",
                recipient_contact=request.user.email,
                subject="Warehouses Imported",
                message=f"Successfully imported {count} warehouses from JSON",
                status="sent"
            )

            messages.success(request, f"Imported {count} warehouses successfully.")
            return redirect("warehouses_list")

    else:
        form = WarehouseImportForm()

    return render(request, "warehouses/import.html", {"form": form})


# ==========================================================
# EXPORT CSV
# ==========================================================

@login_required
@role_required(["admin", "manager"])
def warehouses_export_csv(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM export_warehouses_csv();")
        rows = cursor.fetchall()

    header = "id,name,address,contact,po_schedule_open,po_schedule_close,maximum_storage_capacity\n"
    csv_data = header + "\n".join(r[0] for r in rows)

    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="warehouses_export.csv"'

    # Create notification for the user who exported
    create_notification(
        notification_type="warehouses_exported_csv",
        recipient_contact=request.user.email,
        subject="Warehouses Exported",
        message=f"Successfully exported {len(rows)} warehouses to CSV",
        status="sent"
    )

    return response