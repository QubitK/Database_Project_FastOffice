# ==========================================================
#  INVOICES
# ==========================================================
from datetime import datetime
from decimal import Decimal
import json
from django.db.models import Sum, F
from django.forms import inlineformset_factory

from pyexpat.errors import messages
from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from ..models import Invoice, User , InvoiceItem
from ..forms import InvoiceForm
from .decorators import role_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Prefetch
from ..notifications import create_notification
from xhtml2pdf import pisa
from django.forms import modelformset_factory
from ..models import InvoiceItem
from django.template.loader import get_template
from django.db.models import F, ExpressionWrapper, DecimalField

# Create an inline formset so InvoiceItem is linked to Invoice automatically
InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    fields=["shipment_type", "weight", "delivery_speed", "quantity", "unit_price", "notes"],
    extra=1,        # show one extra blank row for adding a new item
    can_delete=True # allow deleting items
)




@login_required
@role_required(["admin", "client"])
@login_required
@role_required(["admin", "client"])
def invoice_list(request):
    if request.user.role == "client":
        invoices_qs = Invoice.objects.filter(user=request.user).prefetch_related('items').order_by("-invoice_datetime")
    else:
        invoices_qs = Invoice.objects.prefetch_related('items').order_by("-invoice_datetime")

    invoices = []
    for inv in invoices_qs:
        # Compute total_price dynamically for each item
        items = inv.items.annotate(
            total_price=ExpressionWrapper(
                F("quantity") * F("unit_price"),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )

        subtotal = items.aggregate(subtotal=Sum('total_price'))['subtotal'] or 0
        tax = subtotal * Decimal("0.23")
        total = subtotal + tax

        inv.subtotal = subtotal
        inv.tax = tax
        inv.total = total
        inv.items_annotated = items  # pass annotated items to template
        invoices.append(inv)

    return render(request, "invoices/list.html", {"invoices": invoices})

@login_required
@role_required(["admin"])
def invoice_create(request):
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            invoice = form.save()
            formset.instance = invoice
            formset.save()

            create_notification(
                notification_type="invoice_created_admin",
                recipient_contact=request.user.email,
                subject="Invoice Created",
                message=f"Successfully created invoice #{invoice.id_invoice}",
                status="sent",
            )

            return redirect("invoice_list")
    else:
        form = InvoiceForm()
        formset = InvoiceItemFormSet()

    return render(
        request,
        "invoices/create.html",
        {
            "form": form,
            "formset": formset,
        },
    )

@login_required
@role_required(["admin"])
def invoice_edit(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)

        if form.is_valid() and formset.is_valid():
            invoice = form.save()

            formset.instance = invoice
            print(formset.cleaned_data)
            formset.save()

            create_notification(
                notification_type="invoice_updated_admin",
                recipient_contact=request.user.email,
                subject="Invoice Updated",
                message=f"Successfully updated invoice #{invoice.id_invoice}",
                status="sent",
            )

            return redirect("invoice_list")
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)

    return render(
        request,
        "invoices/edit.html",
        {
            "form": form,
            "formset": formset,
            "invoice": invoice,
        },
    )

@login_required
@role_required(["admin"])
def invoice_delete(request, invoice_id):
    """Delete an invoice"""
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method for deletion.")

    invoice = get_object_or_404(Invoice, pk=invoice_id)
    # Store invoice info before deleting
    invoice_info = f"#{invoice.id_invoice} (€{invoice.cost})"

    try:
        invoice.delete()

        # Create notification after successful deletion
        create_notification(
            notification_type="invoice_deleted",
            recipient_contact=request.user.email,
            subject="Invoice Deleted",
            message=f"Successfully deleted invoice {invoice_info}",
            status="sent"
        )

        messages.success(request, "Invoice deleted successfully.")
    except Exception:
        messages.error(request, "An error occurred while deleting the invoice.")

    return redirect("invoice_list")

# ==========================================================
# IMPORT/EXPORT JSON
# ==========================================================

def invoices_import_json(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            messages.error(request, "No file uploaded.")
            return redirect("invoices_import_json")

        try:
            data = json.load(file)
        except Exception:
            messages.error(request, "Invalid JSON.")
            return redirect("invoices_import_json")

        for item in data:
            inv = Invoice(
                id_invoice=item.get("id_invoice"),
                invoice_status=item.get("invoice_status",""),
                invoice_type=item.get("invoice_type",""),
                quantity=item.get("quantity"),
                invoice_datetime=item.get("invoice_datetime"),
                cost=item.get("cost"),
                paid=item.get("paid",False),
                payment_method=item.get("payment_method",""),
                name=item.get("name",""),
                address=item.get("address",""),
                contact=item.get("contact","")
            )

            user_id = item.get("user_id")
            if user_id:
                try:
                    inv.user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    pass

            inv.save()

        messages.success(request, "Invoices imported successfully.")
        return redirect("invoice_list")

    return render(request, "invoices/import.html")

@login_required
@role_required(["admin", "manager"])
def invoices_export_json(request):
    """Export all invoices to JSON"""
    invoices = list(
        Invoice.objects.all().values(
            "id_invoice",
            "invoice_datetime",
            "invoice_status",
            "invoice_type",
            "cost",
            "payment_method",
            "address",
            "contact",
            "quantity",
            "name",
            "paid",
            "user_id",
        )
    )

    for inv in invoices:
        dt = inv.get("invoice_datetime")
        if isinstance(dt, datetime):
            inv["invoice_datetime"] = dt.strftime("%Y-%m-%d %H:%M:%S")

        cost = inv.get("cost")
        if isinstance(cost, Decimal):
            inv["cost"] = float(cost)

        qty = inv.get("quantity")
        if isinstance(qty, Decimal):
            inv["quantity"] = float(qty)

    json_data = json.dumps(invoices, indent=4)
    response = HttpResponse(json_data, content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="invoices_export.json"'

    # Create notification for the user who exported
    create_notification(
        notification_type="invoices_exported",
        recipient_contact=request.user.email,
        subject="Invoices Exported",
        message=f"Successfully exported {len(invoices)} invoices to JSON",
        status="sent"
    )

    return response


# ==================== Export csv ====================
@login_required
@role_required(["admin", "manager"])
def invoices_export_csv(request):
    """Export all invoices to CSV using PostgreSQL function"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM export_invoices_csv();")
        rows = cursor.fetchall()

    header = (
        "id_invoice,invoice_status,invoice_type,quantity,"
        "invoice_datetime,cost,paid,payment_method,"
        "name,address,contact,user_id\n"
    )
    csv_data = header + "\n".join(r[0] for r in rows)

    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="invoices_export.csv"'

    # Create notification for the user who exported
    create_notification(
        notification_type="invoices_exported_csv",
        recipient_contact=request.user.email,
        subject="Invoices Exported",
        message=f"Successfully exported {len(rows)} invoices to CSV",
        status="sent"
    )

    return response

# ==================== Export PDF ====================
# ================== Export PDF ==================
@login_required
@role_required(["admin", "client"])
def invoices_export_pdf(request):
    if request.user.role == "client":
        invoices_qs = Invoice.objects.filter(user=request.user).prefetch_related("items").order_by("-invoice_datetime")
    else:
        invoices_qs = Invoice.objects.prefetch_related("items").order_by("-invoice_datetime")

    invoices = []
    for inv in invoices_qs:
        # Compute totals dynamically
        items = inv.items.annotate(
            total_price=ExpressionWrapper(
                F("quantity") * F("unit_price"),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
        subtotal = items.aggregate(subtotal=Sum("total_price"))["subtotal"] or Decimal("0.00")
        tax = subtotal * Decimal("0.23")
        total = subtotal + tax
        invoices.append({
            "invoice": inv,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "items": items
        })

    template = get_template("invoices/pdf_template.html")
    html = template.render({"invoices": invoices})

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="invoices.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)
    return response