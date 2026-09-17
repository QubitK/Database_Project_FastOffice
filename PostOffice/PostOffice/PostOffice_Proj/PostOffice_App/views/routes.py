# ==========================================================
#  ROUTES — No ORM, uses DB objects only
# ==========================================================
#
#  All database interaction uses django.db.connection (raw psycopg2).
#  No Django model is referenced — reads come from views (v_*),
#  writes go through stored procedures (sp_*), and time validation
#  is handled by trg_route_time_check (BEFORE INSERT/UPDATE).

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import connection
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from ..forms import RouteForm
from ..notifications import create_notification
from .decorators import role_required


# ----------------------------------------------------------
#  LIST   (URL: /routes/   name: "routes_list")
# ----------------------------------------------------------
#  Reads from:
#    - v_routes_full  → routes joined with driver_name, plate_number,
#                        vehicle_name, warehouse_name, etc.
#
#  Python paginates the results (10 per page).

@login_required
def routes_list(request):

    # ---- Step 1: Fetch all routes from the DB view ----
    with connection.cursor() as cur:
        cur.execute("SELECT * FROM v_routes_full")
        columns = [col.name for col in cur.description]
        all_routes = [dict(zip(columns, row)) for row in cur.fetchall()]

    # ---- Step 2: Paginate (10 per page) ----
    paginator = Paginator(all_routes, 10)
    page_number = request.GET.get("page")
    routes = paginator.get_page(page_number)

    # ---- Step 3: Render ----
    return render(request, "routes/list.html", {"routes": routes})


# ----------------------------------------------------------
#  CREATE   (URL: /routes/create/   name: "routes_create")
# ----------------------------------------------------------
#  Writes via:
#    - sp_create_route  → creates route row, returns new id via INOUT
#    - trg_route_time_check fires on INSERT (validates end > start)

@login_required
@role_required(["admin"])
def routes_create(request):
    if request.method == "POST":
        form = RouteForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data

            # CALL sp_create_route(driver_id, vehicle_id, war_id,
            #   description, delivery_status, delivery_date,
            #   delivery_start_time, delivery_end_time,
            #   expected_duration, kms_travelled, driver_notes,
            #   p_id INOUT)
            with connection.cursor() as cur:
                cur.execute(
                    "CALL sp_create_route(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NULL)",
                    [
                        int(cd["driver_id"])  if cd["driver_id"]  else None,
                        int(cd["vehicle_id"]) if cd["vehicle_id"] else None,
                        int(cd["war_id"])     if cd["war_id"]     else None,
                        cd["description"],
                        cd["delivery_status"],
                        cd["delivery_date"],
                        cd["delivery_start_time"] or None,
                        cd["delivery_end_time"]   or None,
                        cd["expected_duration"]   or None,
                        cd["kms_travelled"]       or None,
                        cd["driver_notes"],
                    ],
                )
                route_id = cur.fetchone()[0]

            create_notification(
                notification_type="route_created",
                recipient_contact=request.user.email,
                subject="Route Created",
                message=f"Successfully created route #{route_id}: {cd['description'][:50]}",
                status="sent",
            )

            return redirect("routes_list")

    else:
        form = RouteForm()

    return render(request, "routes/create.html", {"form": form})


# ----------------------------------------------------------
#  EDIT   (URL: /routes/<int:route_id>/edit/   name: "routes_edit")
# ----------------------------------------------------------
#  GET:  Fetch existing route from v_routes_full, pre-populate form.
#  POST: Update route via sp_update_route (COALESCE — NULL keeps existing).
#        trg_route_time_check fires on UPDATE (validates end > start).

@login_required
@role_required(["admin"])
def routes_edit(request, route_id):

    # ---- Fetch existing route ----
    with connection.cursor() as cur:
        cur.execute(
            "SELECT * FROM v_routes_full WHERE id = %s",
            [route_id],
        )
        columns = [col.name for col in cur.description]
        row = cur.fetchone()

    if not row:
        from django.http import Http404
        raise Http404("Route not found")

    route = dict(zip(columns, row))

    if request.method == "POST":
        form = RouteForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data

            # CALL sp_update_route(id, driver_id, vehicle_id, war_id,
            #   description, delivery_status, delivery_date,
            #   delivery_start_time, delivery_end_time,
            #   expected_duration, kms_travelled, driver_notes, is_active)
            with connection.cursor() as cur:
                cur.execute(
                    "CALL sp_update_route(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NULL)",
                    [
                        route_id,
                        int(cd["driver_id"])  if cd["driver_id"]  else None,
                        int(cd["vehicle_id"]) if cd["vehicle_id"] else None,
                        int(cd["war_id"])     if cd["war_id"]     else None,
                        cd["description"],
                        cd["delivery_status"],
                        cd["delivery_date"],
                        cd["delivery_start_time"] or None,
                        cd["delivery_end_time"]   or None,
                        cd["expected_duration"]   or None,
                        cd["kms_travelled"]       or None,
                        cd["driver_notes"],
                    ],
                )

            create_notification(
                notification_type="route_updated",
                recipient_contact=request.user.email,
                subject="Route Updated",
                message=f"Successfully updated route #{route_id}",
                status="sent",
            )

            return redirect("routes_list")

    else:
        # Pre-populate form with existing route data.
        # expected_duration comes from psycopg2 as timedelta; convert to time.
        ed = route["expected_duration"]
        if ed and isinstance(ed, timedelta):
            ed = (datetime.min + ed).time()

        form = RouteForm(initial={
            "driver_id":           route["driver_id"]  or "",
            "vehicle_id":          route["vehicle_id"] or "",
            "war_id":              route["war_id"]     or "",
            "description":         route["description"] or "",
            "delivery_status":     route["delivery_status"],
            "delivery_date":       route["delivery_date"],
            "delivery_start_time": route["delivery_start_time"],
            "delivery_end_time":   route["delivery_end_time"],
            "expected_duration":   ed,
            "kms_travelled":       route["kms_travelled"],
            "driver_notes":        route["driver_notes"] or "",
        })

    return render(request, "routes/edit.html", {
        "form": form,
        "route": route,
        "route_id": route_id,
    })


# ----------------------------------------------------------
#  DELETE   (URL: /routes/<int:route_id>/delete/   name: "routes_delete")
# ----------------------------------------------------------
#  POST only. Calls sp_delete_route (hard-delete).
#  sp_delete_route checks for active deliveries before deleting.

@login_required
@role_required(["admin"])
def routes_delete(request, route_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method for deletion.")

    try:
        with connection.cursor() as cur:
            cur.execute(
                "CALL sp_delete_route(%s)",
                [route_id],
            )

        create_notification(
            notification_type="route_deleted",
            recipient_contact=request.user.email,
            subject="Route Deleted",
            message=f"Successfully deleted route #{route_id}",
            status="sent",
        )

    except Exception:
        # sp_delete_route raises if route not found or has active deliveries.
        pass

    return redirect("routes_list")


# ----------------------------------------------------------
#  IMPORT JSON   (URL: /routes/import/json/   name: "routes_import_json")
# ----------------------------------------------------------
#  Writes via:
#    - sp_import_routes(p_data JSONB)  → bulk-import from JSONB array
#    - trg_route_time_check fires for each inserted row

@login_required
@role_required(["admin", "manager"])
def routes_import_json(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            return redirect("routes_import_json")

        try:
            data = json.load(file)
        except Exception:
            return redirect("routes_import_json")

        if not isinstance(data, list):
            return redirect("routes_import_json")

        # Strip id fields to avoid PK conflicts
        for item in data:
            if isinstance(item, dict) and "id" in item:
                del item["id"]

        # CALL sp_import_routes(p_data JSONB)
        json_str = json.dumps(data)
        with connection.cursor() as cur:
            cur.execute(
                "CALL sp_import_routes(%s::jsonb)",
                [json_str],
            )

        create_notification(
            notification_type="routes_imported",
            recipient_contact=request.user.email,
            subject="Routes Imported",
            message=f"Successfully imported {len(data)} routes from JSON",
            status="sent",
        )

        return redirect("routes_list")

    return render(request, "routes/import.html")


# ----------------------------------------------------------
#  EXPORT JSON   (URL: /routes/export/json/   name: "routes_export_json")
# ----------------------------------------------------------
#  Reads from:
#    - v_routes_export  → flat view with all route columns, ORDER BY id

@login_required
@role_required(["admin", "manager"])
def routes_export_json(request):

    with connection.cursor() as cur:
        cur.execute("SELECT * FROM v_routes_export")
        columns = [col.name for col in cur.description]
        routes = [dict(zip(columns, row)) for row in cur.fetchall()]

    # Serialize non-JSON-native types
    for r in routes:
        for key, val in r.items():
            if isinstance(val, Decimal):
                r[key] = float(val)
            elif isinstance(val, datetime):
                r[key] = val.isoformat()
            elif isinstance(val, date):
                r[key] = val.isoformat()
            elif isinstance(val, timedelta):
                total_seconds = int(val.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                r[key] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            elif isinstance(val, time):
                r[key] = val.isoformat()

    json_data = json.dumps(routes, indent=4)
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="routes_export.json"'

    create_notification(
        notification_type="routes_exported",
        recipient_contact=request.user.email,
        subject="Routes Exported",
        message=f"Successfully exported {len(routes)} routes to JSON",
        status="sent",
    )

    return response


# ----------------------------------------------------------
#  EXPORT CSV   (URL: /routes/export/csv/   name: "routes_export_csv")
# ----------------------------------------------------------
#  Reads from:
#    - v_routes_export  → same flat view as JSON export

@login_required
@role_required(["admin", "manager"])
def routes_export_csv(request):

    with connection.cursor() as cur:
        cur.execute("SELECT * FROM v_routes_export")
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
            elif isinstance(val, datetime):
                cells.append(val.isoformat())
            elif isinstance(val, date):
                cells.append(val.isoformat())
            elif isinstance(val, timedelta):
                total_seconds = int(val.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                cells.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            elif isinstance(val, time):
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
    response["Content-Disposition"] = 'attachment; filename="routes_export.csv"'

    create_notification(
        notification_type="routes_exported_csv",
        recipient_contact=request.user.email,
        subject="Routes Exported",
        message=f"Successfully exported {len(rows)} routes to CSV",
        status="sent",
    )

    return response
