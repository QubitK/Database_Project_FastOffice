# ==========================================================
#  INVOICES — No ORM, uses DB objects only
# ==========================================================
#
#  All database interaction uses django.db.connection (raw psycopg2).
#  No Django model is referenced — reads come from views (v_*),
#  writes go through stored procedures (sp_*), and all business
#  logic (totals, tax, validation) is handled by triggers/functions.

import json
from datetime import date, datetime
from decimal import Decimal

from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from xhtml2pdf import pisa

from ..forms import InvoiceForm, InvoiceItemFormSet
from ..notifications import create_notification
from .decorators import role_required


# ----------------------------------------------------------
#  LIST   (URL: /invoices/   name: "invoice_list")
# ----------------------------------------------------------
#  Reads from:
#    - v_invoices_with_items  → invoice header + warehouse_name, staff_name,
#                                client_name, item_count (all pre-joined by the view)
#    - invoice_item table     → individual items for the expandable sub-table
#
#  No computation in Python — invoice.cost is already correct
#  because triggers recalculate it every time an item is added/edited/deleted.

@login_required
@role_required(["admin", "client"])
def invoice_list(request):

    # ---- Step 1: Fetch invoices from the DB view ----
    # v_invoices_with_items returns one row per invoice with all
    # joined info (warehouse_name, staff_name, client_name, item_count).
    # Clients only see their own invoices (filtered by client_id).
    # Admins see all invoices.
    with connection.cursor() as cur:
        if request.user.role == "client":
            cur.execute(
                "SELECT * FROM v_invoices_with_items WHERE client_id = %s",
                [request.user.id],
            )
        else:
            cur.execute("SELECT * FROM v_invoices_with_items")

        # Convert cursor rows into a list of dicts.
        # cur.description gives us column names; zip pairs them with each row's values.
        # Result: [{"id": 1, "status": "pending", "cost": 123.45, ...}, ...]
        columns = [col.name for col in cur.description]
        invoices = [dict(zip(columns, row)) for row in cur.fetchall()]

    # ---- Step 2: Fetch items for the expandable sub-table ----
    # The list template shows a nested table of items under each invoice.
    # We fetch ALL items for ALL displayed invoices in a single query
    # (using ANY(%s) with a list of ids), then group them by inv_id in Python.
    # This avoids N+1 queries (one query per invoice).
    if invoices:
        inv_ids = [inv["id"] for inv in invoices]

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, inv_id, shipment_type, weight, delivery_speed,
                       quantity, unit_price, total_item_cost, notes
                FROM invoice_item
                WHERE inv_id = ANY(%s)
                ORDER BY id
                """,
                [inv_ids],
                # ANY(%s) with a Python list → psycopg2 converts it to
                # a PostgreSQL array: ANY(ARRAY[1, 2, 3])
            )
            columns = [col.name for col in cur.description]
            all_items = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Group items by their parent invoice id.
        # setdefault creates a new list the first time a key is seen.
        # Result: {1: [item_dict, item_dict], 2: [item_dict], ...}
        items_by_inv = {}
        for item in all_items:
            items_by_inv.setdefault(item["inv_id"], []).append(item)

        # Attach the items list to each invoice dict.
        # In the template: {% for item in inv.items %}
        # (Django templates access dict keys with dot notation)
        for inv in invoices:
            inv["items"] = items_by_inv.get(inv["id"], [])

    # ---- Step 3: Render ----
    # Pass the list of invoice dicts to the template.
    # Each dict has keys matching v_invoices_with_items columns
    # plus an "items" key containing a list of item dicts.
    return render(request, "invoices/list.html", {"invoices": invoices})


# ----------------------------------------------------------
#  CREATE   (URL: /invoices/create/   name: "invoice_create")
# ----------------------------------------------------------
#  Writes via:
#    1. sp_create_invoice  → creates the invoice header row, returns the new id
#    2. sp_add_invoice_item → creates each item row (one CALL per item)
#
#  After each sp_add_invoice_item CALL, the DB automatically:
#    - trg_invoice_item_calc_total fires (BEFORE INSERT on invoice_item)
#        → calls fn_calculate_item_total(qty, unit_price)
#        → sets invoice_item.total_item_cost
#    - trg_invoice_update_cost fires (AFTER INSERT on invoice_item)
#        → calls fn_invoice_total(invoice_id)
#            → calls fn_invoice_subtotal (SUM of all items)
#            → calls fn_calculate_tax (subtotal × 0.23)
#        → updates invoice.cost and invoice.quantity
#
#  So Django only collects form data and calls procedures.
#  Zero business logic in Python.

@login_required
@role_required(["admin"])
def invoice_create(request):
    if request.method == "POST":
        # Bind the submitted POST data to the form and formset for validation.
        # InvoiceForm validates the invoice header fields.
        # InvoiceItemFormSet validates each item row the user filled in.
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # cleaned_data is a dict of validated, type-converted values.
            # e.g. cd["war_id"] is a string (from ChoiceField), cd["paid"] is a bool
            cd = form.cleaned_data

            # ---- Step 1: Create invoice header ----
            # CALL sp_create_invoice(p_war_id, p_staff_id, p_client_id,
            #   p_status, p_type, p_quantity, p_cost, p_paid, p_pay_method,
            #   p_name, p_address, p_contact, p_id INOUT)
            #
            # The last parameter (NULL) is the INOUT p_id — PostgreSQL returns
            # the newly generated invoice.id through it after the INSERT.
            # cur.fetchone()[0] retrieves that returned id.
            #
            # ChoiceField returns strings for war_id/staff_id/client_id,
            # so we convert to int (sp_create_invoice expects INT parameters).
            # Empty string "" means "nothing selected" → pass None.
            with connection.cursor() as cur:
                cur.execute(
                    "CALL sp_create_invoice(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NULL)",
                    [
                        int(cd["war_id"])    if cd["war_id"]    else None,  # FK → warehouse
                        int(cd["staff_id"])  if cd["staff_id"]  else None,  # FK → employee_staff
                        int(cd["client_id"]) if cd["client_id"] else None,  # FK → client
                        cd["status"],       # e.g. "pending"
                        cd["type"],         # e.g. "paid_on_send"
                        0,                  # quantity — triggers will recalculate from items
                        0,                  # cost     — triggers will recalculate from items
                        cd["paid"],         # bool
                        cd["pay_method"],   # e.g. "cash"
                        cd["name"],         # invoice recipient name
                        cd["address"],      # invoice recipient address
                        cd["contact"],      # invoice recipient contact
                    ],
                )
                # Fetch the INOUT return value — the new invoice's id
                invoice_id = cur.fetchone()[0]

            # ---- Step 2: Add each invoice item ----
            # Loop through the formset. Each form represents one item row.
            # has_changed() returns False for blank extra rows the user didn't touch.
            # DELETE flag is True if the user checked the delete checkbox (for edit forms).
            #
            # CALL sp_add_invoice_item(p_inv_id, p_shipment_type, p_weight,
            #   p_delivery_speed, p_quantity, p_unit_price, p_notes, p_id INOUT)
            #
            # After each CALL, the trigger chain fires automatically:
            #   trg_invoice_item_calc_total → sets this item's total_item_cost
            #   trg_invoice_update_cost     → recalculates parent invoice.cost
            for item_form in formset:
                # Skip blank extra rows that the user didn't fill in
                if not item_form.has_changed():
                    continue

                icd = item_form.cleaned_data

                # Skip rows marked for deletion
                if icd.get("DELETE"):
                    continue

                with connection.cursor() as cur:
                    cur.execute(
                        "CALL sp_add_invoice_item(%s,%s,%s,%s,%s,%s,%s, NULL)",
                        [
                            invoice_id,             # FK → the invoice we just created
                            icd["shipment_type"],   # e.g. "package", "letter"
                            icd["weight"],          # Decimal or None
                            icd["delivery_speed"],  # e.g. "standard", "express"
                            icd["quantity"],         # int, min 1
                            icd["unit_price"],       # Decimal, min 0
                            icd.get("notes"),       # optional text
                        ],
                    )
                    # We don't need the returned item id here,
                    # but the INOUT NULL is still required by the procedure signature.

            # ---- Step 3: Send notification (MongoDB — unchanged) ----
            create_notification(
                notification_type="invoice_created_admin",
                recipient_contact=request.user.email,
                subject="Invoice Created",
                message=f"Successfully created invoice #{invoice_id}",
                status="sent",
            )

            # ---- Step 4: Redirect to list page ----
            return redirect("invoice_list")

    else:
        # GET request — show empty form + formset
        # InvoiceForm.__init__ queries the DB to populate FK dropdown choices.
        # InvoiceItemFormSet shows 1 blank item row (extra=1).
        form = InvoiceForm()
        formset = InvoiceItemFormSet()

    return render(request, "invoices/create.html", {
        "form": form,
        "formset": formset,
    })


# ----------------------------------------------------------
#  EDIT   (URL: /invoices/<int:invoice_id>/edit/   name: "invoice_edit")
# ----------------------------------------------------------
#  GET:  Fetch existing invoice + items from DB, pre-populate form + formset.
#  POST: Update invoice header via sp_update_invoice,
#        delete all existing items (raw DELETE),
#        re-insert items from formset via sp_add_invoice_item.
#
#  Why delete-and-recreate items instead of updating in place?
#  - We don't have sp_update_invoice_item or sp_delete_invoice_item
#  - The existing triggers already handle DELETE and INSERT on invoice_item
#  - trg_invoice_update_cost recalculates invoice.cost after each operation
#  - Item IDs get regenerated (new serial values), but items are only ever
#    accessed through their parent invoice, so this doesn't matter.

@login_required
@role_required(["admin"])
def invoice_edit(request, invoice_id):

    # ---- Fetch existing invoice (used by both GET and POST-with-errors) ----
    # We need the current invoice data to:
    #   - Pre-populate the form on GET
    #   - Re-populate the form if POST validation fails
    #   - Return 404 if the invoice doesn't exist
    with connection.cursor() as cur:
        cur.execute(
            "SELECT * FROM v_invoices_with_items WHERE id = %s",
            [invoice_id],
        )
        columns = [col.name for col in cur.description]
        row = cur.fetchone()

    # If no row returned, the invoice doesn't exist → 404
    if not row:
        from django.http import Http404
        raise Http404("Invoice not found")

    # Convert the single row to a dict for easy field access
    # e.g. invoice["war_id"], invoice["status"], invoice["client_name"], etc.
    invoice = dict(zip(columns, row))

    # ---- Fetch existing items for formset pre-population ----
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, inv_id, shipment_type, weight, delivery_speed,
                   quantity, unit_price, total_item_cost, notes
            FROM invoice_item
            WHERE inv_id = %s
            ORDER BY id
            """,
            [invoice_id],
        )
        columns = [col.name for col in cur.description]
        existing_items = [dict(zip(columns, r)) for r in cur.fetchall()]

    if request.method == "POST":
        # Bind POST data to form and formset for validation
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            cd = form.cleaned_data

            # ---- Step 1: Update invoice header ----
            # CALL sp_update_invoice(p_id, p_war_id, p_staff_id, p_client_id,
            #   p_status, p_type, p_quantity, p_cost, p_paid, p_pay_method,
            #   p_name, p_address, p_contact)
            #
            # sp_update_invoice uses COALESCE — any NULL parameter keeps
            # the existing value. But here we pass all values from the form
            # since the user may have changed any field.
            with connection.cursor() as cur:
                cur.execute(
                    "CALL sp_update_invoice(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    [
                        invoice_id,                                          # p_id
                        int(cd["war_id"])    if cd["war_id"]    else None,   # FK → warehouse
                        int(cd["staff_id"])  if cd["staff_id"]  else None,   # FK → employee_staff
                        int(cd["client_id"]) if cd["client_id"] else None,   # FK → client
                        cd["status"],       # e.g. "pending"
                        cd["type"],         # e.g. "paid_on_send"
                        None,               # quantity — triggers will recalculate from items
                        None,               # cost     — triggers will recalculate from items
                        cd["paid"],         # bool
                        cd["pay_method"],   # e.g. "cash"
                        cd["name"],         # invoice recipient name
                        cd["address"],      # invoice recipient address
                        cd["contact"],      # invoice recipient contact
                    ],
                )

            # ---- Step 2: Delete all existing items ----
            # Raw DELETE — no procedure needed.
            # trg_invoice_update_cost fires for each deleted row,
            # recalculating invoice.cost (goes to 0 after all items deleted).
            with connection.cursor() as cur:
                cur.execute(
                    "DELETE FROM invoice_item WHERE inv_id = %s",
                    [invoice_id],
                )

            # ---- Step 3: Re-insert items from formset ----
            # Same logic as invoice_create: loop through formset,
            # skip blank/deleted rows, CALL sp_add_invoice_item for each.
            # After each insert, triggers recalculate:
            #   trg_invoice_item_calc_total → sets total_item_cost
            #   trg_invoice_update_cost     → updates invoice.cost
            for item_form in formset:
                if not item_form.has_changed():
                    continue
                icd = item_form.cleaned_data
                if icd.get("DELETE"):
                    continue

                with connection.cursor() as cur:
                    cur.execute(
                        "CALL sp_add_invoice_item(%s,%s,%s,%s,%s,%s,%s, NULL)",
                        [
                            invoice_id,
                            icd["shipment_type"],
                            icd["weight"],
                            icd["delivery_speed"],
                            icd["quantity"],
                            icd["unit_price"],
                            icd.get("notes"),
                        ],
                    )

            # ---- Step 4: Notification (MongoDB) ----
            create_notification(
                notification_type="invoice_updated_admin",
                recipient_contact=request.user.email,
                subject="Invoice Updated",
                message=f"Successfully updated invoice #{invoice_id}",
                status="sent",
            )

            return redirect("invoice_list")

    else:
        # ---- GET: Pre-populate form with existing invoice data ----
        # Pass initial={...} to InvoiceForm so the fields show current values.
        # The dict keys must match the form field names exactly.
        # ChoiceField initial values are ints from the DB — Django matches them
        # against the choice tuples loaded in __init__ to select the right option.
        form = InvoiceForm(initial={
            "war_id":     invoice["war_id"],      # int or None → selects dropdown option
            "staff_id":   invoice["staff_id"],     # int or None
            "client_id":  invoice["client_id"],    # int or None
            "status":     invoice["status"],       # e.g. "pending"
            "type":       invoice["type"],         # e.g. "paid_on_send"
            "paid":       invoice["paid"],         # bool
            "pay_method": invoice["pay_method"],   # e.g. "cash"
            "name":       invoice["name"] or "",   # text
            "address":    invoice["address"] or "", # text
            "contact":    invoice["contact"] or "", # text
        })

        # ---- GET: Pre-populate formset with existing items ----
        # formset_factory accepts initial=[dict, dict, ...] where each dict
        # has keys matching the form field names.
        # With extra=1, Django shows len(initial) pre-filled rows + 1 blank row.
        # e.g. 3 existing items → 3 pre-filled + 1 blank = 4 rows shown.
        formset = InvoiceItemFormSet(initial=[
            {
                "shipment_type":  item["shipment_type"],
                "weight":         item["weight"],
                "delivery_speed": item["delivery_speed"],
                "quantity":       item["quantity"],
                "unit_price":     item["unit_price"],
                "notes":          item["notes"] or "",
            }
            for item in existing_items
        ])

    # Pass both the form/formset AND the invoice dict to the template.
    # The template needs invoice["id"] for the form action URL and display.
    return render(request, "invoices/edit.html", {
        "form": form,
        "formset": formset,
        "invoice": invoice,
    })


# ----------------------------------------------------------
#  DELETE   (URL: /invoices/<int:invoice_id>/delete/   name: "invoice_delete")
# ----------------------------------------------------------
#  POST only — rejects GET requests.
#
#  Calls sp_delete_invoice which issues a DELETE FROM invoice.
#  But trg_invoice_soft_delete (BEFORE DELETE trigger) intercepts it:
#    - Sets invoice.status = 'cancelled'
#    - Returns NULL to cancel the actual DELETE
#  So the row stays in the table with status='cancelled'.
#
#  sp_delete_invoice then verifies the row exists with status='cancelled'.
#  If the invoice didn't exist, it raises an exception.

@login_required
@role_required(["admin"])
def invoice_delete(request, invoice_id):
    # Only allow POST requests for deletion (safety measure)
    if request.method != "POST":
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest("Invalid request method for deletion.")

    try:
        # CALL sp_delete_invoice(p_id)
        # This triggers the soft-delete: status → 'cancelled', row stays in DB.
        # If invoice doesn't exist, the procedure raises an exception.
        with connection.cursor() as cur:
            cur.execute(
                "CALL sp_delete_invoice(%s)",
                [invoice_id],
            )

        # Notification (MongoDB)
        create_notification(
            notification_type="invoice_deleted",
            recipient_contact=request.user.email,
            subject="Invoice Deleted",
            message=f"Successfully deleted (cancelled) invoice #{invoice_id}",
            status="sent",
        )

    except Exception:
        # sp_delete_invoice raises if invoice not found.
        # In production you might want to log this or show an error message.
        pass

    return redirect("invoice_list")


# ----------------------------------------------------------
#  IMPORT JSON   (URL: /invoices/import/json/   name: "invoices_import_json")
# ----------------------------------------------------------
#  Writes via:
#    - sp_import_invoices(p_data JSONB)  → bulk-import from JSONB array
#      supports optional nested "items" array per invoice element
#      triggers fire for each inserted item:
#        trg_invoice_item_calc_total → sets total_item_cost
#        trg_invoice_update_cost    → recalculates invoice.cost

@login_required
@role_required(["admin", "manager"])
def invoices_import_json(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            return redirect("invoices_import_json")

        try:
            data = json.load(file)
        except Exception:
            return redirect("invoices_import_json")

        if not isinstance(data, list):
            return redirect("invoices_import_json")

        # Strip id fields to avoid PK conflicts
        for item in data:
            if isinstance(item, dict):
                item.pop("id", None)
                # Also strip item ids from nested items
                for sub in item.get("items", []):
                    if isinstance(sub, dict):
                        sub.pop("id", None)

        # CALL sp_import_invoices(p_data JSONB)
        json_str = json.dumps(data)
        with connection.cursor() as cur:
            cur.execute(
                "CALL sp_import_invoices(%s::jsonb)",
                [json_str],
            )

        create_notification(
            notification_type="invoices_imported",
            recipient_contact=request.user.email,
            subject="Invoices Imported",
            message=f"Successfully imported {len(data)} invoices from JSON",
            status="sent",
        )

        return redirect("invoice_list")

    return render(request, "invoices/import.html")


# ----------------------------------------------------------
#  EXPORT JSON   (URL: /invoices/export/json/   name: "invoices_export_json")
# ----------------------------------------------------------
#  Reads from:
#    - v_invoices_export  → flat view with all invoice columns, ORDER BY id
#
#  Python serializes Decimal/datetime values, dumps to JSON,
#  and returns an HttpResponse with Content-Disposition attachment.

@login_required
@role_required(["admin", "manager"])
def invoices_export_json(request):

    # ---- Step 1: Fetch all invoices from the export view ----
    with connection.cursor() as cur:
        cur.execute("SELECT * FROM v_invoices_export")
        columns = [col.name for col in cur.description]
        invoices = [dict(zip(columns, row)) for row in cur.fetchall()]

    # ---- Step 2: Serialize non-JSON-native types ----
    # Decimal → float, datetime/date → ISO string
    for inv in invoices:
        for key, val in inv.items():
            if isinstance(val, Decimal):
                inv[key] = float(val)
            elif isinstance(val, (datetime, date)):
                inv[key] = val.isoformat()

    # ---- Step 3: Build JSON response as file download ----
    json_data = json.dumps(invoices, indent=4)
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="invoices_export.json"'

    # ---- Step 4: Notification (MongoDB) ----
    create_notification(
        notification_type="invoices_exported",
        recipient_contact=request.user.email,
        subject="Invoices Exported",
        message=f"Successfully exported {len(invoices)} invoices to JSON",
        status="sent",
    )

    return response


# ----------------------------------------------------------
#  EXPORT CSV   (URL: /invoices/export/csv/   name: "invoices_export_csv")
# ----------------------------------------------------------
#  Reads from:
#    - v_invoices_export  → same flat view as JSON export
#
#  Python builds a CSV string (header + rows) from the view data.

@login_required
@role_required(["admin", "manager"])
def invoices_export_csv(request):

    # ---- Step 1: Fetch all invoices from the export view ----
    with connection.cursor() as cur:
        cur.execute("SELECT * FROM v_invoices_export")
        columns = [col.name for col in cur.description]
        rows = cur.fetchall()

    # ---- Step 2: Build CSV string ----
    # Header line from column names
    header = ",".join(columns)
    # Data lines — convert each value to string, escape commas in text fields
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
                # Wrap in quotes if the value contains commas or quotes
                if "," in s or '"' in s:
                    s = '"' + s.replace('"', '""') + '"'
                cells.append(s)
        lines.append(",".join(cells))

    csv_data = header + "\n" + "\n".join(lines)

    # ---- Step 3: Build CSV response as file download ----
    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="invoices_export.csv"'

    # ---- Step 4: Notification (MongoDB) ----
    create_notification(
        notification_type="invoices_exported_csv",
        recipient_contact=request.user.email,
        subject="Invoices Exported",
        message=f"Successfully exported {len(rows)} invoices to CSV",
        status="sent",
    )

    return response


# ----------------------------------------------------------
#  EXPORT PDF   (URL: /invoices/export/pdf/   name: "invoices_export_pdf")
# ----------------------------------------------------------
#  Reads from:
#    - v_invoices_with_items  → invoice header + warehouse_name, staff_name,
#                                client_name, item_count
#    - invoice_item table     → line items per invoice
#
#  invoice.cost already contains subtotal + 23% tax (computed by triggers).
#  For the PDF breakdown we compute subtotal from items in Python (0 extra DB calls).
#  pdf_template.html uses {{ item.total_item_cost }} (matches DB column directly).

@login_required
@role_required(["admin", "client"])
def invoices_export_pdf(request):

    # ---- Step 1: Fetch invoices ----
    # Clients see only their own invoices; admins see all.
    with connection.cursor() as cur:
        if request.user.role == "client":
            cur.execute(
                "SELECT * FROM v_invoices_with_items WHERE client_id = %s",
                [request.user.id],
            )
        else:
            cur.execute("SELECT * FROM v_invoices_with_items")

        columns = [col.name for col in cur.description]
        invoices = [dict(zip(columns, row)) for row in cur.fetchall()]

    # ---- Step 2: Fetch items for all invoices in a single query ----
    if invoices:
        inv_ids = [inv["id"] for inv in invoices]

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, inv_id, shipment_type, weight, delivery_speed,
                       quantity, unit_price, total_item_cost, notes
                FROM invoice_item
                WHERE inv_id = ANY(%s)
                ORDER BY id
                """,
                [inv_ids],
            )
            item_columns = [col.name for col in cur.description]
            all_items = [dict(zip(item_columns, r)) for r in cur.fetchall()]
    else:
        all_items = []

    # Group items by invoice id
    items_by_inv = {}
    for item in all_items:
        items_by_inv.setdefault(item["inv_id"], []).append(item)

    # ---- Step 3: Build template context with subtotal/tax/total per invoice ----
    # Subtotal = SUM(total_item_cost) from items (already computed by trigger 15)
    # Tax = subtotal × 0.23
    # Total = subtotal + tax  (should match invoice.cost from trigger 16)
    pdf_invoices = []
    for inv in invoices:
        items = items_by_inv.get(inv["id"], [])
        subtotal = sum(item["total_item_cost"] or Decimal("0.00") for item in items)
        tax = (subtotal * Decimal("0.23")).quantize(Decimal("0.01"))
        total = subtotal + tax

        pdf_invoices.append({
            "invoice": inv,
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
        })

    # ---- Step 4: Render HTML → PDF via xhtml2pdf ----
    template = get_template("invoices/pdf_template.html")
    html = template.render({"invoices": pdf_invoices})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="invoices.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    return response
