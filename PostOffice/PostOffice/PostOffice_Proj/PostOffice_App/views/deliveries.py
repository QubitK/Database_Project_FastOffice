# PostOffice_App/views/deliveries.py
# ==========================================================
#  DELIVERIES (SQL-FIRST, NO ORM) + FORMS VALIDATION
# ==========================================================

import csv
import json
from io import StringIO

from django.db import connection
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest

# IMPORTANT: deliveries.py is inside PostOffice_App/views/
# forms.py is in PostOffice_App/
from ..forms import (
    DeliveryCreateForm,
    DeliveryEditForm,
    DeliveryStatusUpdateForm,
    DeliveryImportJSONForm,   # if you created it; if not, remove and see note below
)


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ----------------------------------------------------------
# LIST DELIVERIES
# ----------------------------------------------------------

@login_required
def deliveries_list(request):
    role = request.user.role
    user_id = request.user.id

    with connection.cursor() as cursor:
        if role == "client":
            cursor.execute("SELECT * FROM fn_get_client_deliveries(%s);", [user_id])
        elif role == "employee":
            cursor.execute("SELECT * FROM fn_get_driver_deliveries(%s);", [user_id])
        else:
            cursor.execute("SELECT * FROM v_deliveries_full;")

        deliveries = dictfetchall(cursor)

    return render(request, "deliveries/list.html", {"deliveries": deliveries})


# ----------------------------------------------------------
# DELIVERY DETAIL
# ----------------------------------------------------------

@login_required
def deliveries_detail(request, delivery_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM v_deliveries_full WHERE id = %s;", [delivery_id])
        rows = dictfetchall(cursor)

    if not rows:
        messages.error(request, "Delivery not found.")
        return redirect("deliveries_list")

    delivery = rows[0]
    return render(request, "deliveries/detail.html", {"delivery": delivery})


# ----------------------------------------------------------
# CREATE DELIVERY (WITH VALIDATION)
# ----------------------------------------------------------

@login_required
def deliveries_create(request):
    if request.method == "POST":
        form = DeliveryCreateForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        CALL sp_create_delivery(
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s,
                            %s
                        );
                        """,
                        [
                            cd.get("driver_id"),
                            cd.get("route_id"),
                            cd.get("inv_id"),
                            cd.get("client_id"),
                            cd.get("war_id"),
                            cd.get("tracking_number"),
                            cd.get("description"),
                            cd.get("sender_name"),
                            cd.get("sender_address"),
                            cd.get("sender_phone"),
                            cd.get("sender_email"),
                            cd.get("recipient_name"),
                            cd.get("recipient_address"),
                            cd.get("recipient_phone"),
                            cd.get("recipient_email"),
                            cd.get("item_type"),
                            cd.get("weight"),
                            cd.get("dimensions"),
                            cd.get("status"),
                            cd.get("priority"),
                            cd.get("delivery_date"),
                            None,  # OUT p_id
                        ],
                    )

                messages.success(request, "Delivery created successfully.")
                return redirect("deliveries_list")

            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Fix the errors in the form.")
    else:
        form = DeliveryCreateForm()

    return render(request, "deliveries/create.html", {"form": form})


# ----------------------------------------------------------
# EDIT DELIVERY (WITH VALIDATION)
# ----------------------------------------------------------

@login_required
def deliveries_edit(request, delivery_id):
    # 1) Load delivery for GET (and also for POST errors to re-render)
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM v_deliveries_full WHERE id = %s;", [delivery_id])
        rows = dictfetchall(cursor)

    if not rows:
        messages.error(request, "Delivery not found.")
        return redirect("deliveries_list")

    delivery = rows[0]

    if request.method == "POST":
        form = DeliveryEditForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        CALL sp_update_delivery(
                            %s::int,
                            %s::int, %s::int, %s::int, %s::int, %s::int,
                            %s::varchar, %s::text,
                            %s::varchar, %s::text, %s::varchar, %s::varchar,
                            %s::varchar, %s::text, %s::varchar, %s::varchar,
                            %s::varchar, %s::int, %s::varchar,
                            %s::varchar, %s::bool,
                            %s::timestamptz
                        );
                        """,
                        [
                            delivery_id,
                            cd.get("driver_id"),
                            cd.get("route_id"),
                            cd.get("inv_id"),
                            cd.get("client_id"),
                            cd.get("war_id"),
                            cd.get("tracking_number"),
                            cd.get("description"),
                            cd.get("sender_name"),
                            cd.get("sender_address"),
                            cd.get("sender_phone"),
                            cd.get("sender_email"),
                            cd.get("recipient_name"),
                            cd.get("recipient_address"),
                            cd.get("recipient_phone"),
                            cd.get("recipient_email"),
                            cd.get("item_type"),
                            cd.get("weight"),
                            cd.get("dimensions"),
                            cd.get("priority"),
                            cd.get("in_transition"),
                            cd.get("delivery_date"),
                        ],
                    )

                messages.success(request, "Delivery updated successfully.")
                return redirect("deliveries_detail", delivery_id=delivery_id)

            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Fix the errors in the form.")

        # IMPORTANT: re-render with BOTH form and delivery
        return render(
            request,
            "deliveries/edit.html",
            {"delivery_id": delivery_id, "form": form, "delivery": delivery},
        )

    # GET: prefill from delivery
    form = DeliveryEditForm(initial={
        "driver_id": delivery.get("driver_id"),
        "route_id": delivery.get("route_id"),
        "inv_id": delivery.get("inv_id"),
        "client_id": delivery.get("client_id"),
        "war_id": delivery.get("war_id"),
        "tracking_number": delivery.get("tracking_number"),
        "description": delivery.get("description"),
        "sender_name": delivery.get("sender_name"),
        "sender_address": delivery.get("sender_address"),
        "sender_phone": delivery.get("sender_phone"),
        "sender_email": delivery.get("sender_email"),
        "recipient_name": delivery.get("recipient_name"),
        "recipient_address": delivery.get("recipient_address"),
        "recipient_phone": delivery.get("recipient_phone"),
        "recipient_email": delivery.get("recipient_email"),
        "item_type": delivery.get("item_type"),
        "weight": delivery.get("weight"),
        "dimensions": delivery.get("dimensions"),
        "priority": delivery.get("priority"),
        "in_transition": delivery.get("in_transition"),
        "delivery_date": delivery.get("delivery_date"),
    })

    return render(
        request,
        "deliveries/edit.html",
        {"delivery_id": delivery_id, "form": form, "delivery": delivery},
    )



# ----------------------------------------------------------
# UPDATE DELIVERY STATUS (WITH VALIDATION)
# ----------------------------------------------------------

def deliveries_update_status(request, delivery_id):
    if request.method != "POST":
        return redirect("deliveries_detail", delivery_id=delivery_id)

    form = DeliveryStatusUpdateForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CALL sp_update_delivery_status(%s, %s);",
                    [delivery_id, cd["status"]],
                )
                cursor.execute("REFRESH MATERIALIZED VIEW mv_delivery_tracking;")
            messages.success(request, "Delivery status updated.")
        except Exception as e:
            # IMPORTANTE: esto te dice la verdad
            messages.error(request, f"Status update failed: {e}")
    else:
        messages.error(request, "Fix the errors in the status form.")

    return redirect("deliveries_detail", delivery_id=delivery_id)



# ----------------------------------------------------------
# DELETE DELIVERY (SOFT DELETE)
# ----------------------------------------------------------

@login_required
def deliveries_delete(request, delivery_id):
    if request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("CALL sp_delete_delivery(%s);", [delivery_id])

            messages.success(request, "Delivery cancelled successfully.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("deliveries_list")


# ----------------------------------------------------------
# DELIVERIES EXPORT JSON
# ----------------------------------------------------------

@login_required
def deliveries_export_json(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM v_deliveries_full ORDER BY id;")
        deliveries = dictfetchall(cursor)

    json_data = json.dumps(deliveries, default=str, indent=4)
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="deliveries_export.json"'
    return response


# ----------------------------------------------------------
# DELIVERIES IMPORT JSON (WITH VALIDATION)
# ----------------------------------------------------------

@login_required
def deliveries_import_json(request):
    if request.method == "POST":
        # If you didn't create DeliveryImportJSONForm, replace this block with:
        # file = request.FILES.get("file") ...
        form = DeliveryImportJSONForm(request.POST, request.FILES)

        if not form.is_valid():
            return HttpResponseBadRequest("No file uploaded or invalid form.")

        file = form.cleaned_data["file"]

        try:
            data = json.load(file)
        except Exception:
            return HttpResponseBadRequest("Invalid JSON file.")

        if not isinstance(data, list):
            return HttpResponseBadRequest("JSON must contain a list of deliveries.")

        created_count = 0
        skipped_count = 0

        with connection.cursor() as cursor:
            for item in data:
                if not isinstance(item, dict):
                    skipped_count += 1
                    continue

                # Validate each item with the SAME form rules
                item_form = DeliveryCreateForm(item)
                if not item_form.is_valid():
                    skipped_count += 1
                    continue

                cd = item_form.cleaned_data
                try:
                    cursor.execute(
                        """
                        CALL sp_create_delivery(
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s,
                            %s
                        );
                        """,
                        [
                            cd.get("driver_id"),
                            cd.get("route_id"),
                            cd.get("inv_id"),
                            cd.get("client_id"),
                            cd.get("war_id"),
                            cd.get("tracking_number"),
                            cd.get("description"),
                            cd.get("sender_name"),
                            cd.get("sender_address"),
                            cd.get("sender_phone"),
                            cd.get("sender_email"),
                            cd.get("recipient_name"),
                            cd.get("recipient_address"),
                            cd.get("recipient_phone"),
                            cd.get("recipient_email"),
                            cd.get("item_type"),
                            cd.get("weight"),
                            cd.get("dimensions"),
                            cd.get("status"),
                            cd.get("priority"),
                            cd.get("delivery_date"),
                            None,  # OUT p_id
                        ],
                    )
                    created_count += 1
                except Exception:
                    skipped_count += 1
                    continue

        if created_count:
            messages.success(request, f"Imported {created_count} deliveries successfully.")
        if skipped_count:
            messages.warning(request, f"Skipped {skipped_count} invalid deliveries.")

        return redirect("deliveries_list")

    # GET
    form = DeliveryImportJSONForm()
    return render(request, "deliveries/import.html", {"form": form})


# ----------------------------------------------------------
# DELIVERIES EXPORT CSV
# ----------------------------------------------------------

@login_required
def deliveries_export_csv(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM v_deliveries_full ORDER BY id;")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)

    for row in rows:
        writer.writerow([("" if v is None else str(v)) for v in row])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="deliveries_export.csv"'
    return response


# ----------------------------------------------------------
# DELIVERIES
# ----------------------------------------------------------

@login_required
def delivery_tracking_view(request, delivery_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tracking_number,
                status,
                notes,
                staff_name,
                warehouse_name,
                event_timestamp
            FROM v_delivery_tracking
            WHERE delivery_id = %s
            ORDER BY event_timestamp ASC;
            """,
            [delivery_id],
        )
        rows = cursor.fetchall()

    tracking = [
        {
            "tracking_number": r[0],
            "status": r[1],
            "notes": r[2],
            "staff_name": r[3],
            "warehouse_name": r[4],
            "event_timestamp": r[5],
        }
        for r in rows
    ]

    return render(request, "deliveries/tracking.html", {"tracking": tracking})

@login_required
def deliveries_tracking(request, tracking_number):
    # 1) Timeline de tracking desde la MATERIALIZED VIEW
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                delivery_id,
                tracking_number,
                tracking_id,
                status,
                notes,
                event_timestamp,
                staff_id,
                staff_username,
                warehouse_id,
                warehouse_name
            FROM mv_delivery_tracking
            WHERE tracking_number = %s
            ORDER BY event_timestamp ASC, tracking_id ASC;
            """,
            [tracking_number],
        )
        tracking = dictfetchall(cursor)

    # 2) delivery_id from tracking events, or look up delivery directly
    if tracking:
        delivery_id = tracking[0].get("delivery_id")
    else:
        delivery_id = None

    # 3) Info "bonita" del delivery (v_deliveries_full)
    delivery = None
    if delivery_id is not None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM v_deliveries_full WHERE id = %s;", [delivery_id])
            rows = dictfetchall(cursor)
        delivery = rows[0] if rows else None
    else:
        # No tracking events — try to find the delivery by tracking_number directly
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM v_deliveries_full WHERE tracking_number = %s;", [tracking_number])
            rows = dictfetchall(cursor)
        if rows:
            delivery = rows[0]
            delivery_id = delivery["id"]

    if not tracking:
        messages.error(request, "No tracking events found for this tracking number.")

    # 4) Render
    return render(
        request,
        "deliveries/tracking.html",
        {
            "tracking_number": tracking_number,
            "delivery_id": delivery_id,
            "delivery": delivery or {},
            "tracking": tracking,
        },
    )