# ==========================================================
#  VEHICLES — No ORM, uses DB objects only
# ==========================================================
#
#  All database interaction uses django.db.connection (raw psycopg2).
#  No Django model is referenced — reads come from views (v_*),
#  writes go through stored procedures (sp_*), and year validation
#  is handled by fn_is_valid_year inside the procedures.

import json
from datetime import date, datetime
from decimal import Decimal

from django.db import connection
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from ..forms import VehicleForm
from ..notifications import create_notification
from .decorators import role_required


# ----------------------------------------------------------
#  LIST   (URL: /vehicles/   name: "vehicles_list")
# ----------------------------------------------------------
#  Reads from:
#    - v_vehicles_full  → all vehicle columns, ORDER BY id
#
#  Python paginates the results (10 per page).

@login_required
@role_required(["admin", "manager", "staff"])
def vehicles_list(request):

    # ---- Step 1: Fetch all vehicles from the DB view ----
    with connection.cursor() as cur:
        cur.execute("SELECT * FROM v_vehicles_full")
        columns = [col.name for col in cur.description]
        all_vehicles = [dict(zip(columns, row)) for row in cur.fetchall()]

    # ---- Step 2: Paginate (10 per page) ----
    paginator = Paginator(all_vehicles, 10)
    page_number = request.GET.get("page")
    vehicles = paginator.get_page(page_number)

    # ---- Step 3: Render ----
    return render(request, "vehicles/list.html", {"vehicles": vehicles})


# ----------------------------------------------------------
#  CREATE   (URL: /vehicles/create/   name: "vehicles_create")
# ----------------------------------------------------------
#  Writes via:
#    - sp_create_vehicle  → creates vehicle row, returns new id via INOUT
#      internally calls fn_is_valid_year(year) for validation

@login_required
@role_required(["admin", "manager"])
def vehicles_create(request):
    if request.method == "POST":
        form = VehicleForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data

            # CALL sp_create_vehicle(vehicle_type, plate_number, capacity,
            #   brand, model, vehicle_status, year, fuel_type,
            #   last_maintenance_date, p_id INOUT)
            with connection.cursor() as cur:
                cur.execute(
                    "CALL sp_create_vehicle(%s,%s,%s,%s,%s,%s,%s,%s,%s, NULL)",
                    [
                        cd["vehicle_type"],
                        cd["plate_number"],
                        cd["capacity"],
                        cd["brand"],
                        cd["model"],
                        cd["vehicle_status"],
                        cd["year"],
                        cd["fuel_type"],
                        cd["last_maintenance_date"],
                    ],
                )
                vehicle_id = cur.fetchone()[0]

            create_notification(
                notification_type="vehicle_created",
                recipient_contact=request.user.email,
                subject="Vehicle Created",
                message=f"Successfully created vehicle #{vehicle_id}: {cd['plate_number']}",
                status="sent",
            )

            return redirect("vehicles_list")

    else:
        form = VehicleForm()

    return render(request, "vehicles/create.html", {"form": form})


# ----------------------------------------------------------
#  EDIT   (URL: /vehicles/<int:vehicle_id>/edit/   name: "vehicles_edit")
# ----------------------------------------------------------
#  GET:  Fetch existing vehicle from v_vehicles_full, pre-populate form.
#  POST: Update vehicle via sp_update_vehicle (COALESCE — NULL keeps existing).
#        sp_update_vehicle calls fn_is_valid_year if year is provided.

@login_required
@role_required(["admin", "manager"])
def vehicles_edit(request, vehicle_id):

    # ---- Fetch existing vehicle ----
    with connection.cursor() as cur:
        cur.execute(
            "SELECT * FROM v_vehicles_full WHERE id = %s",
            [vehicle_id],
        )
        columns = [col.name for col in cur.description]
        row = cur.fetchone()

    if not row:
        from django.http import Http404
        raise Http404("Vehicle not found")

    vehicle = dict(zip(columns, row))

    if request.method == "POST":
        form = VehicleForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data

            # CALL sp_update_vehicle(id, vehicle_type, plate_number, capacity,
            #   brand, model, vehicle_status, year, fuel_type,
            #   last_maintenance_date, is_active)
            with connection.cursor() as cur:
                cur.execute(
                    "CALL sp_update_vehicle(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NULL)",
                    [
                        vehicle_id,
                        cd["vehicle_type"],
                        cd["plate_number"],
                        cd["capacity"],
                        cd["brand"],
                        cd["model"],
                        cd["vehicle_status"],
                        cd["year"],
                        cd["fuel_type"],
                        cd["last_maintenance_date"],
                    ],
                )

            create_notification(
                notification_type="vehicle_updated",
                recipient_contact=request.user.email,
                subject="Vehicle Updated",
                message=f"Successfully updated vehicle #{vehicle_id}: {cd['plate_number']}",
                status="sent",
            )

            return redirect("vehicles_list")

    else:
        # Pre-populate form with existing vehicle data
        form = VehicleForm(initial={
            "vehicle_type":          vehicle["vehicle_type"],
            "plate_number":          vehicle["plate_number"],
            "capacity":              vehicle["capacity"],
            "brand":                 vehicle["brand"] or "",
            "model":                 vehicle["model"] or "",
            "vehicle_status":        vehicle["vehicle_status"],
            "year":                  vehicle["year"],
            "fuel_type":             vehicle["fuel_type"],
            "last_maintenance_date": vehicle["last_maintenance_date"],
        })

    return render(request, "vehicles/edit.html", {
        "form": form,
        "vehicle": vehicle,
        "vehicle_id": vehicle_id,
    })


# ----------------------------------------------------------
#  DELETE   (URL: /vehicles/<int:vehicle_id>/delete/   name: "vehicles_delete")
# ----------------------------------------------------------
#  POST only. Calls sp_delete_vehicle (hard-delete).
#  sp_delete_vehicle checks for active routes before deleting.

@login_required
@role_required(["admin"])
def vehicles_delete(request, vehicle_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method for deletion.")

    try:
        with connection.cursor() as cur:
            cur.execute(
                "CALL sp_delete_vehicle(%s)",
                [vehicle_id],
            )

        create_notification(
            notification_type="vehicle_deleted",
            recipient_contact=request.user.email,
            subject="Vehicle Deleted",
            message=f"Successfully deleted vehicle #{vehicle_id}",
            status="sent",
        )

    except Exception:
        # sp_delete_vehicle raises if vehicle not found or has active routes.
        pass

    return redirect("vehicles_list")


# ----------------------------------------------------------
#  IMPORT JSON   (URL: /vehicles/import/json/   name: "vehicles_import_json")
# ----------------------------------------------------------
#  Writes via:
#    - sp_import_vehicles(p_data JSONB)  → bulk-import from JSONB array
#      internally calls fn_is_valid_year for each element

@login_required
@role_required(["admin", "manager"])
def vehicles_import_json(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            return redirect("vehicles_import_json")

        try:
            data = json.load(file)
        except Exception:
            return redirect("vehicles_import_json")

        if not isinstance(data, list):
            return redirect("vehicles_import_json")

        # Strip id fields to avoid PK conflicts
        for item in data:
            if isinstance(item, dict) and "id" in item:
                del item["id"]

        # CALL sp_import_vehicles(p_data JSONB)
        json_str = json.dumps(data)
        with connection.cursor() as cur:
            cur.execute(
                "CALL sp_import_vehicles(%s::jsonb)",
                [json_str],
            )

        create_notification(
            notification_type="vehicles_imported",
            recipient_contact=request.user.email,
            subject="Vehicles Imported",
            message=f"Successfully imported {len(data)} vehicles from JSON",
            status="sent",
        )

        return redirect("vehicles_list")

    return render(request, "vehicles/import.html")


# ----------------------------------------------------------
#  EXPORT JSON   (URL: /vehicles/export/json/   name: "vehicles_export_json")
# ----------------------------------------------------------
#  Reads from:
#    - v_vehicles_export  → flat view with all vehicle columns, ORDER BY id

@login_required
@role_required(["admin", "manager", "staff"])
def vehicles_export_json(request):

    with connection.cursor() as cur:
        cur.execute("SELECT * FROM v_vehicles_export")
        columns = [col.name for col in cur.description]
        vehicles = [dict(zip(columns, row)) for row in cur.fetchall()]

    # Serialize non-JSON-native types
    for v in vehicles:
        for key, val in v.items():
            if isinstance(val, Decimal):
                v[key] = float(val)
            elif isinstance(val, (datetime, date)):
                v[key] = val.isoformat()

    json_data = json.dumps(vehicles, indent=4)
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="vehicles_export.json"'

    create_notification(
        notification_type="vehicles_exported",
        recipient_contact=request.user.email,
        subject="Vehicles Exported",
        message=f"Successfully exported {len(vehicles)} vehicles to JSON",
        status="sent",
    )

    return response


# ----------------------------------------------------------
#  EXPORT CSV   (URL: /vehicles/export/csv/   name: "vehicles_export_csv")
# ----------------------------------------------------------
#  Reads from:
#    - v_vehicles_export  → same flat view as JSON export

@login_required
@role_required(["admin", "manager"])
def vehicles_export_csv(request):

    with connection.cursor() as cur:
        cur.execute("SELECT * FROM v_vehicles_export")
        columns = [col.name for col in cur.description]
        rows = cur.fetchall()

    # Build CSV string
    header = ",".join(columns)
    lines = []
    for row in rows:
        cells = []
        for val in row:
            if val is None:
                cells.append("")
            elif isinstance(val, bool):
                cells.append("true" if val else "false")
            elif isinstance(val, (datetime, date)):
                cells.append(val.isoformat())
            elif isinstance(val, Decimal):
                cells.append(str(val))
            else:
                s = str(val)
                if "," in s or '"' in s:
                    s = '"' + s.replace('"', '""') + '"'
                cells.append(s)
        lines.append(",".join(cells))

    csv_data = header + "\n" + "\n".join(lines)

    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="vehicles_export.csv"'

    create_notification(
        notification_type="vehicles_exported_csv",
        recipient_contact=request.user.email,
        subject="Vehicles Exported",
        message=f"Successfully exported {len(rows)} vehicles to CSV",
        status="sent",
    )

    return response
