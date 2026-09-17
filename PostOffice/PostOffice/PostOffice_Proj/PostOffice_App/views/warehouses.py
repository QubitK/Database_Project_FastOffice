import json

from django.db import connection
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ..forms import WarehouseForm
from ..notifications import create_notification

from .decorators import role_required


# # ==========================================================
# #  WAREHOUSES
# # ==========================================================
# from datetime import datetime, time
# from decimal import Decimal
# import json
# from pyexpat.errors import messages
# from django.db import connection
# from django.shortcuts import render, get_object_or_404, redirect
# from django.http import HttpResponse, HttpResponseBadRequest

# from ..forms import WarehouseForm

# from ..models import Warehouse
# from ..forms import WarehouseImportForm
# from .decorators import role_required
# from django.contrib.auth.decorators import login_required
# from django.core.paginator import Paginator

# from ..notifications import create_notification

# @login_required
# @role_required(["admin"])
# def warehouses_list(request):
#     warehouses_qs = Warehouse.objects.all()
#     paginator = Paginator(warehouses_qs, 10)
#     page_number = request.GET.get("page")
#     warehouses_page = paginator.get_page(page_number)
#     return render(request, "warehouses/list.html", {"warehouses": warehouses_page})


@login_required
@role_required(["admin", "manager"])
def warehouses_list(request):
    """
    List of warehouses using SQL view v_warehouses_full.
    """

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM v_warehouses_full
            ORDER BY name
        """)
        columns = [col[0] for col in cursor.description]
        warehouses = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(
        request,
        "warehouses/list.html",
        {"warehouses": warehouses},
    )


# @login_required
# @role_required(["admin"])
# def warehouses_create(request):
#     if request.method == "POST":
#         form = WarehouseForm(request.POST)
#         if form.is_valid():
#             # Save the warehouse and get the instance
#             warehouse = form.save()

#             # Create notification for the admin who created it
#             create_notification(
#                 notification_type="warehouse_created",
#                 recipient_contact=request.user.email,  # Send to current admin
#                 subject="Warehouse Created",
#                 message=f"Successfully created warehouse: {warehouse.name}",
#                 status="sent"
#             )

#             return redirect("warehouses_list")
#     else:
#         form = WarehouseForm()
#     return render(request, "warehouses/create.html", {"form": form})


@login_required
@role_required(["admin", "manager"])
def warehouses_create(request):
    if request.method == "POST":
        form = WarehouseForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CALL sp_create_warehouse(
                        %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    [
                        cd["name"],
                        cd.get("contact"),
                        cd["address"],
                        cd["maximum_storage_capacity"],
                        cd.get("po_schedule_open"),
                        cd.get("po_schedule_close"),
                        cd.get("schedule"),
                    ],
                )

            create_notification(
                notification_type="warehouse_created",
                recipient_contact=request.user.email,
                subject="Warehouse created",
                message=f"Warehouse '{cd['name']}' was created successfully.",
                status="sent",
            )

            return redirect("warehouses_list")

    else:
        form = WarehouseForm()

    return render(request, "warehouses/create.html", {"form": form})

# @login_required
# @role_required(["admin", "staff"])
# def warehouses_edit(request, warehouse_id):
#     warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
#     if request.method == "POST":
#         form = WarehouseForm(request.POST, instance=warehouse)
#         if form.is_valid():
#             # Save the updated warehouse
#             form.save()

#             # Create notification for the user who edited it
#             create_notification(
#                 notification_type="warehouse_updated",
#                 recipient_contact=request.user.email,  # Send to current user (admin/staff)
#                 subject="Warehouse Updated",
#                 message=f"Successfully updated warehouse: {warehouse.name}",
#                 status="sent"
#             )

#             messages.success(request, "Warehouse updated successfully.")
#             return redirect("warehouses_list")
#     else:
#         form = WarehouseForm(instance=warehouse)
#     return render(
#         request,
#         "warehouses/edit.html",
#         {"form": form, "warehouse_id": warehouse_id},
#     )


@login_required
@role_required(["admin", "manager"])
def warehouses_edit(request, warehouse_id):
    """
    Edit an existing warehouse using sp_update_warehouse.
    Validation is done via WarehouseForm.
    Persistence is handled by PostgreSQL stored procedure.
    """

    # Obtener nombre ANTES de editar (para la notificación)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM v_warehouses_full WHERE id = %s",
            [warehouse_id],
        )
        row = cursor.fetchone()

    old_name = row[0] if row else f"ID {warehouse_id}"

    if request.method == "POST":
        form = WarehouseForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CALL sp_update_warehouse(
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    [
                        warehouse_id,
                        cd["name"],
                        cd["contact"],
                        cd["address"],
                        cd["po_schedule_open"],
                        cd["po_schedule_close"],
                        None,  # schedule (derived)
                        cd["maximum_storage_capacity"],
                        cd.get("is_active", True),
                    ],
                )

            create_notification(
                notification_type="warehouse_updated",
                recipient_contact=request.user.email,
                subject="Warehouse updated",
                message=(
                    f"Warehouse '{old_name}' was updated."
                    if cd["name"] == old_name
                    else f"Warehouse '{old_name}' was renamed to '{cd['name']}'."
                ),
                status="sent",
            )

            return redirect("warehouses_list")

    else:
        form = WarehouseForm()

    return render(
        request,
        "warehouses/edit.html",
        {
            "form": form,
            "warehouse_id": warehouse_id,
        },
    )

# @login_required
# @role_required(["admin"])
# def warehouses_delete(request, warehouse_id):
#     if request.method != "POST":
#         return HttpResponseBadRequest("Invalid request method for deletion.")

#     warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
#     # Store the warehouse name before deleting
#     warehouse_name = warehouse.name

#     try:
#         warehouse.delete()

#         # Create notification after successful deletion
#         create_notification(
#             notification_type="warehouse_deleted",
#             recipient_contact=request.user.email,  # Send to admin who deleted it
#             subject="Warehouse Deleted",
#             message=f"Successfully deleted warehouse: {warehouse_name}",
#             status="sent"
#         )

#         messages.success(request, "Warehouse deleted successfully.")
#     except Exception:
#         messages.error(request, "An error occurred while deleting the warehouse.")

#     return redirect("warehouses_list")


@login_required
@role_required(["admin", "manager"])
def warehouses_delete(request, warehouse_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")

    # Obtener nombre ANTES de borrar
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM v_warehouses_full WHERE id = %s",
            [warehouse_id],
        )
        row = cursor.fetchone()

    warehouse_name = row[0] if row else f"ID {warehouse_id}"

    # Borrado real
    with connection.cursor() as cursor:
        cursor.execute(
            "CALL sp_delete_warehouse(%s)",
            [warehouse_id],
        )

    create_notification(
        notification_type="warehouse_deleted",
        recipient_contact=request.user.email,
        subject="Warehouse deleted",
        message=f"Warehouse '{warehouse_name}' was deleted.",
        status="sent",
    )

    return redirect("warehouses_list")


# # ==========================================================
# # IMPORT/EXPORT JSON
# # ==========================================================

# @login_required
# @role_required(["admin", "manager"])
# def warehouses_export_json(request):
#     warehouses = list(
#         Warehouse.objects.all().values(
#             "id",
#             "name",
#             "address",
#             "contact",
#             "po_schedule_open",
#             "po_schedule_close",
#             "maximum_storage_capacity",
#         )
#     )

#     cleaned = []
#     for w in warehouses:
#         w = dict(w)
#         for field in ("po_schedule_open", "po_schedule_close"):
#             val = w.get(field)
#             if isinstance(val, time):
#                 w[field] = val.strftime("%H:%M:%S")
#         cleaned.append(w)

#     json_data = json.dumps(cleaned, indent=4)
#     response = HttpResponse(json_data, content_type="application/json")
#     response["Content-Disposition"] = 'attachment; filename="warehouses_export.json"'

#     # Create notification for the user who exported
#     create_notification(
#         notification_type="warehouses_exported",
#         recipient_contact=request.user.email,
#         subject="Warehouses Exported",
#         message=f"Successfully exported {len(cleaned)} warehouses to JSON",
#         status="sent"
#     )

#     return response



@login_required
@role_required(["admin", "manager"])
def warehouses_export_json(request):
    """
    Export warehouses to JSON using v_warehouses_export view.
    """

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM v_warehouses_export
            ORDER BY id
        """)
        columns = [col[0] for col in cursor.description]
        warehouses = [dict(zip(columns, row)) for row in cursor.fetchall()]

    json_data = json.dumps(warehouses, default=str, indent=4)

    response = HttpResponse(
        json_data,
        content_type="application/json"
    )
    response["Content-Disposition"] = 'attachment; filename="warehouses_export.json"'

    return response



# @login_required
# @role_required(["admin"])
# def warehouses_import_json(request):
#     if request.method == "POST":
#         form = WarehouseImportForm(request.POST, request.FILES)

#         if form.is_valid():
#             file = request.FILES["file"]

#             # Load JSON safely
#             try:
#                 data = json.load(file)
#             except Exception:
#                 messages.error(request, "Invalid JSON file.")
#                 return redirect("warehouses_import_json")

#             if not isinstance(data, list):
#                 messages.error(request, "JSON must contain a list of warehouses.")
#                 return redirect("warehouses_import_json")

#             count = 0

#             for raw in data:
#                 if not isinstance(raw, dict):
#                     continue

#                 item = dict(raw)  # isolate mutation

#                 # =====================================================
#                 # 1. STRIP ANY PRIMARY KEY FIELD (absolute protection)
#                 # =====================================================
#                 for key in list(item.keys()):
#                     if "id" in key.lower():
#                         item.pop(key, None)

#                 # =====================================================
#                 # 2. MAP BOTH IMPORT & EXPORT FIELD NAMES
#                 # =====================================================
#                 name = item.get("name")

#                 address = (
#                     item.get("address")
#                     or item.get("location")
#                 )

#                 contact = item.get("contact")

#                 po_open = item.get("po_schedule_open")
#                 po_close = item.get("po_schedule_close")

#                 max_capacity = (
#                     item.get("maximum_storage_capacity")
#                     or item.get("capacity")
#                 )

#                 # =====================================================
#                 # 3. VALIDATE required NOT NULL fields manually
#                 # =====================================================
#                 if not name or not address:
#                     continue

#                 # =====================================================
#                 # 4. CREATE SAFE NEW WAREHOUSE ENTRY
#                 # =====================================================
#                 Warehouse.objects.create(
#                     name=name,
#                     address=address,
#                     contact=contact,
#                     po_schedule_open=po_open,
#                     po_schedule_close=po_close,
#                     maximum_storage_capacity=max_capacity,
#                 )

#                 count += 1

#             # Create notification for the user who imported
#             create_notification(
#                 notification_type="warehouses_imported",
#                 recipient_contact=request.user.email,
#                 subject="Warehouses Imported",
#                 message=f"Successfully imported {count} warehouses from JSON",
#                 status="sent"
#             )

#             messages.success(request, f"Imported {count} warehouses successfully.")
#             return redirect("warehouses_list")

#     else:
#         form = WarehouseImportForm()

#     return render(request, "warehouses/import.html", {"form": form})

@login_required
@role_required(["admin", "manager"])
def warehouses_import_json(request):
    """
    Import warehouses from a JSON file using sp_create_warehouse.
    All validation and constraints are enforced at DB level.
    """

    if request.method != "POST":
        return render(request, "warehouses/import.html")

    file = request.FILES.get("file")
    if not file:
        return HttpResponseBadRequest("No file uploaded.")

    try:
        data = json.load(file)
    except Exception:
        return HttpResponseBadRequest("Invalid JSON file.")

    if not isinstance(data, list):
        return HttpResponseBadRequest("JSON must contain a list of warehouses.")

    created_count = 0
    skipped_count = 0

    with connection.cursor() as cursor:
        for item in data:
            if not isinstance(item, dict):
                skipped_count += 1
                continue

            try:
                cursor.execute(
                    """
                    CALL sp_create_warehouse(
                        %s,  -- name
                        %s,  -- contact
                        %s,  -- address
                        %s,  -- maximum_storage_capacity
                        %s,  -- schedule_open
                        %s,  -- schedule_close
                        %s   -- schedule
                    )
                    """,
                    [
                        item.get("name"),
                        item.get("contact"),
                        item.get("address"),
                        item.get("maximum_storage_capacity"),
                        item.get("schedule_open"),
                        item.get("schedule_close"),
                        item.get("schedule"),
                    ],
                )
                created_count += 1
            except Exception:
                skipped_count += 1
                continue

    create_notification(
        notification_type="warehouses_imported",
        recipient_contact=request.user.email,
        subject="Warehouses imported",
        message=(
            f"Imported {created_count} warehouses from JSON."
            + (f" Skipped {skipped_count} invalid entries." if skipped_count else "")
        ),
        status="sent",
    )

    return redirect("warehouses_list")


# # ==========================================================
# # EXPORT CSV
# # ==========================================================

# @login_required
# @role_required(["admin", "manager"])
# def warehouses_export_csv(request):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT * FROM export_warehouses_csv();")
#         rows = cursor.fetchall()

#     header = "id,name,address,contact,po_schedule_open,po_schedule_close,maximum_storage_capacity\n"
#     csv_data = header + "\n".join(r[0] for r in rows)

#     response = HttpResponse(csv_data, content_type="text/csv")
#     response["Content-Disposition"] = 'attachment; filename="warehouses_export.csv"'

#     # Create notification for the user who exported
#     create_notification(
#         notification_type="warehouses_exported_csv",
#         recipient_contact=request.user.email,
#         subject="Warehouses Exported",
#         message=f"Successfully exported {len(rows)} warehouses to CSV",
#         status="sent"
#     )

#     return response




@login_required
@role_required(["admin", "manager"])
def warehouses_export_csv(request):
    """
    Export warehouses to CSV using export_warehouses_csv() SQL function.
    """

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM export_warehouses_csv();")
        rows = cursor.fetchall()

    header = (
        "id,"
        "name,"
        "contact,"
        "address,"
        "schedule_open,"
        "schedule_close,"
        "schedule,"
        "maximum_storage_capacity,"
        "is_active,"
        "created_at,"
        "updated_at\n"
    )

    csv_lines = []
    for row in rows:
        csv_lines.append(
            ",".join("" if value is None else str(value) for value in row)
        )

    csv_data = header + "\n".join(csv_lines)

    create_notification(
        notification_type="warehouses_exported_csv",
        recipient_contact=request.user.email,
        subject="Warehouses exported (CSV)",
        message=f"Successfully exported {len(rows)} warehouses to CSV.",
        status="sent",
    )

    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="warehouses_export.csv"'

    return response

