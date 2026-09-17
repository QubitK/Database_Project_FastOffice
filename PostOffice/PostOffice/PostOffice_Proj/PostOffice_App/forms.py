from django import forms
from django.db import connection
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User
# NOTE: Only User is imported — all other models (Invoice, Vehicle, Route, etc.)
# were removed from models.py. Those tables are now DDL-managed.


# ==========================================================
#  USER FORMS (still Django ORM — User is the only ORM model)
# ==========================================================

# LEAVE THIS COMMENTED ???
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "contact", "address", "role", "password1", "password2"
        ]


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "contact", "address", "role"
        ]


USER_ROLE_CHOICES = [
    ("admin", "Admin"),
    ("client", "Client"),
    ("driver", "Driver"),
    ("staff", "Staff"),
    ("manager", "Manager"),
]


class UserForm(forms.Form):
    """
    Generic USER form.
    Used only for validation and cleaned_data.
    DB persistence is done via stored procedures.
    """

    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Required only when creating a new user",
    )

    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    contact = forms.CharField(max_length=20, required=False)
    address = forms.CharField(max_length=255, required=False)

    role = forms.ChoiceField(choices=USER_ROLE_CHOICES)
    is_active = forms.BooleanField(required=False, initial=True)
# ==========================================================
#  INVOICE FORM  (plain Form — matches DDL INVOICE table)
# ==========================================================
#
#  Why plain forms.Form instead of ModelForm?
#  - The Invoice Django model no longer exists in models.py
#  - The INVOICE table is created by DDL.sql, not Django migrations
#  - All CRUD goes through stored procedures, not ORM .save()
#  - Field names here match DDL column names exactly
#    (e.g. "status" not "invoice_status", "pay_method" not "payment_method")
#
#  These choice lists match the CHECK constraints in DDL.sql:
#    CHK_INVOICE_STATUS, CHK_INVOICE_TYPE, CHK_INVOICE_PAY_METHOD

INVOICE_STATUS_CHOICES = [
    ("pending",    "Pending"),
    ("completed",  "Completed"),
    ("cancelled",  "Cancelled"),
    ("refunded",   "Refunded"),
]

INVOICE_TYPE_CHOICES = [
    ("paid_on_send",     "Paid on Send"),
    ("paid_on_delivery", "Paid on Delivery"),
]

PAY_METHOD_CHOICES = [
    ("cash",           "Cash"),
    ("card",           "Card"),
    ("mobile_payment", "Mobile Payment"),
    ("account",        "Account"),
]


class InvoiceForm(forms.Form):
    # --- FK dropdowns ---
    # These are ChoiceField, NOT ModelChoiceField (no model to query).
    # Choices are loaded dynamically from the DB in __init__ below.
    # ChoiceField returns strings, so the view converts to int before
    # passing to sp_create_invoice (which expects INT parameters).
    war_id    = forms.ChoiceField(label="Warehouse",     required=False)
    staff_id  = forms.ChoiceField(label="Staff Member",  required=False)
    client_id = forms.ChoiceField(label="Client",        required=False)

    # --- Invoice header fields ---
    # These map 1:1 to DDL INVOICE columns and sp_create_invoice parameters
    status     = forms.ChoiceField(choices=INVOICE_STATUS_CHOICES, initial="pending", label="Status")
    type       = forms.ChoiceField(choices=INVOICE_TYPE_CHOICES,   label="Invoice Type")
    paid       = forms.BooleanField(required=False, initial=False, label="Paid")
    pay_method = forms.ChoiceField(choices=PAY_METHOD_CHOICES,     label="Payment Method")

    # --- Contact/address fields ---
    name    = forms.CharField(max_length=255, required=False, label="Name")
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False, label="Address")
    contact = forms.CharField(max_length=255, required=False, label="Contact")

    # NOTE: "quantity" and "cost" are NOT form fields.
    # They are auto-calculated by DB triggers when invoice items are added:
    #   trg_invoice_update_cost → fn_invoice_total → fn_invoice_subtotal + fn_calculate_tax
    # The view passes 0 for both when calling sp_create_invoice.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate FK dropdown choices from the database.
        # Each query fetches (id, display_name) pairs.
        # The empty tuple ("", "---------") is the default "nothing selected" option.
        with connection.cursor() as cur:

            # Warehouses — only active ones
            cur.execute("SELECT id, name FROM warehouse WHERE is_active = true ORDER BY name")
            self.fields["war_id"].choices = [("", "---------")] + [
                (r[0], r[1]) for r in cur.fetchall()
            ]

            # Staff members — join employee_staff → USER to get full name
            cur.execute("""
                SELECT es.id, u.first_name || ' ' || u.last_name
                FROM employee_staff es
                JOIN "USER" u ON u.id = es.id
                ORDER BY u.first_name
            """)
            self.fields["staff_id"].choices = [("", "---------")] + [
                (r[0], r[1]) for r in cur.fetchall()
            ]

            # Clients — join client → USER to get full name
            cur.execute("""
                SELECT c.id, u.first_name || ' ' || u.last_name
                FROM client c
                JOIN "USER" u ON u.id = c.id
                ORDER BY u.first_name
            """)
            self.fields["client_id"].choices = [("", "---------")] + [
                (r[0], r[1]) for r in cur.fetchall()
            ]


# ==========================================================
#  INVOICE ITEM FORM + FORMSET
# ==========================================================
#
#  Each field maps to a parameter of sp_add_invoice_item:
#    sp_add_invoice_item(p_inv_id, p_shipment_type, p_weight,
#                        p_delivery_speed, p_quantity, p_unit_price, p_notes)
#
#  Fields NOT included here (handled automatically by DB triggers):
#    - total_item_cost → set by trg_invoice_item_calc_total (qty × unit_price)
#    - invoice.cost    → updated by trg_invoice_update_cost (sum of items + 23% tax)
#    - inv_id          → passed in the view, not a form field

class InvoiceItemForm(forms.Form):
    shipment_type  = forms.CharField(max_length=50, required=False, label="Shipment Type")
    weight         = forms.DecimalField(max_digits=10, decimal_places=2, required=False, label="Weight (kg)")
    delivery_speed = forms.CharField(max_length=50, required=False, label="Delivery Speed")
    quantity       = forms.IntegerField(min_value=1, label="Quantity")
    unit_price     = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, label="Unit Price (€)")
    notes          = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False, label="Notes")


from django.forms import formset_factory

# formset_factory creates a collection of InvoiceItemForm instances.
# - extra=1    → show 1 blank row for adding a new item
# - can_delete → adds a DELETE checkbox to each row (used in edit, but also
#                needed here so formset validation handles it correctly)
#
# Old code used inlineformset_factory(Invoice, InvoiceItem, ...) which
# required both Django models. formset_factory works with plain Form classes.
InvoiceItemFormSet = formset_factory(
    InvoiceItemForm,
    extra=1,
    can_delete=True,
)


# ==========================================================
#  VEHICLE FORM  (plain Form — matches DDL VEHICLE table)
# ==========================================================
#
#  Field names match DDL column names exactly.
#  Choice lists match the CHECK constraints in DDL.sql:
#    CHK_VEHICLE_TYPE, CHK_VEHICLE_STATUS, CHK_VEHICLE_FUEL

VEHICLE_TYPE_CHOICES = [
    ("van",        "Van"),
    ("truck",      "Truck"),
    ("motorcycle", "Motorcycle"),
    ("bicycle",    "Bicycle"),
    ("car",        "Car"),
]

VEHICLE_STATUS_CHOICES = [
    ("available",      "Available"),
    ("in_use",         "In Use"),
    ("maintenance",    "Maintenance"),
    ("out_of_service", "Out of Service"),
]

VEHICLE_FUEL_CHOICES = [
    ("diesel",   "Diesel"),
    ("petrol",   "Petrol"),
    ("electric", "Electric"),
    ("hybrid",   "Hybrid"),
]


class VehicleForm(forms.Form):
    vehicle_type          = forms.ChoiceField(choices=VEHICLE_TYPE_CHOICES, label="Vehicle Type")
    plate_number          = forms.CharField(max_length=20, label="Plate Number")
    capacity              = forms.DecimalField(max_digits=10, decimal_places=2, required=False, label="Capacity (kg)")
    brand                 = forms.CharField(max_length=50, required=False, label="Brand")
    model                 = forms.CharField(max_length=50, required=False, label="Model")
    vehicle_status        = forms.ChoiceField(choices=VEHICLE_STATUS_CHOICES, initial="available", label="Status")
    year                  = forms.IntegerField(label="Year")
    fuel_type             = forms.ChoiceField(choices=VEHICLE_FUEL_CHOICES, label="Fuel Type")
    last_maintenance_date = forms.DateField(required=False, label="Last Maintenance Date",
                                            widget=forms.DateInput(attrs={"type": "date"}))


# ==========================================================
#  ROUTE FORM  (plain Form — matches DDL ROUTE table)
# ==========================================================
#
#  Field names match DDL column names exactly.
#  Choice list matches the CHECK constraint in DDL.sql:
#    CHK_ROUTE_STATUS

ROUTE_STATUS_CHOICES = [
    ("not_started", "Not Started"),
    ("on_going",    "On Going"),
    ("finished",    "Finished"),
    ("cancelled",   "Cancelled"),
]


class RouteForm(forms.Form):
    # --- FK dropdowns ---
    driver_id  = forms.ChoiceField(label="Driver",    required=False)
    vehicle_id = forms.ChoiceField(label="Vehicle",   required=False)
    war_id     = forms.ChoiceField(label="Warehouse", required=False)

    # --- Route fields ---
    description      = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False, label="Description")
    delivery_status  = forms.ChoiceField(choices=ROUTE_STATUS_CHOICES, initial="not_started", label="Status")
    delivery_date    = forms.DateField(required=False, label="Delivery Date",
                                       widget=forms.DateInput(attrs={"type": "date"}))
    delivery_start_time = forms.DateTimeField(
        required=False, label="Start Time",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"],
    )
    delivery_end_time = forms.DateTimeField(
        required=False, label="End Time",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"],
    )
    expected_duration = forms.TimeField(required=False, label="Expected Duration",
                                        widget=forms.TimeInput(attrs={"type": "time"}))
    kms_travelled    = forms.DecimalField(max_digits=8, decimal_places=2, required=False, label="KMs Travelled")
    driver_notes     = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False, label="Driver Notes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        with connection.cursor() as cur:

            # Drivers — employee_driver JOIN USER to get full name
            cur.execute("""
                SELECT ed.id, u.first_name || ' ' || u.last_name
                FROM employee_driver ed
                JOIN "USER" u ON u.id = ed.id
                ORDER BY u.first_name
            """)
            self.fields["driver_id"].choices = [("", "---------")] + [
                (r[0], r[1]) for r in cur.fetchall()
            ]

            # Vehicles — active vehicles with plate + brand/model
            cur.execute("""
                SELECT id, plate_number || ' (' || brand || ' ' || model || ')'
                FROM vehicle
                WHERE is_active = true
                ORDER BY plate_number
            """)
            self.fields["vehicle_id"].choices = [("", "---------")] + [
                (r[0], r[1]) for r in cur.fetchall()
            ]

            # Warehouses — only active ones
            cur.execute("SELECT id, name FROM warehouse WHERE is_active = true ORDER BY name")
            self.fields["war_id"].choices = [("", "---------")] + [
                (r[0], r[1]) for r in cur.fetchall()
            ]


# ===============
#  EMPLOYEE FORMS
# ===============
from django import forms

class EmployeeForm(forms.Form):
    # ---------- USER ----------
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput(), required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    contact = forms.CharField(max_length=20, required=False)
    address = forms.CharField(max_length=255, required=False)

    # ---------- EMPLOYEE ----------
    war_id = forms.IntegerField()
    emp_position = forms.ChoiceField(
        choices=[
            ("driver", "Driver"),
            ("staff", "Staff"),
        ]
    )
    schedule = forms.CharField(required=False)
    wage = forms.DecimalField(required=False, min_value=0)
    hire_date = forms.DateField(required=False)
    is_active = forms.BooleanField(required=False)


class EmployeeDriverForm(forms.Form):
    license_number = forms.CharField(required=False)
    license_category = forms.ChoiceField(
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        required=False,
    )
    license_expiry = forms.DateField(required=False)
    driving_experience = forms.IntegerField(required=False, min_value=0)
    driver_status = forms.ChoiceField(
        choices=[
            ("available", "Available"),
            ("on_duty", "On duty"),
            ("off_duty", "Off duty"),
            ("on_break", "On break"),
        ],
        required=False,
    )


class EmployeeStaffForm(forms.Form):
    department = forms.ChoiceField(
        choices=[
            ("customer_service", "Customer service"),
            ("sorting", "Sorting"),
            ("administration", "Administration"),
        ],
        required=False,
    )

# ==========================================================
#  WAREHOUSE FORM
# ==========================================================
class WarehouseForm(forms.Form):
    name = forms.CharField(max_length=100)
    address = forms.CharField(max_length=255)
    contact = forms.CharField(max_length=100, required=False)

    po_schedule_open = forms.TimeField(required=False)
    po_schedule_close = forms.TimeField(required=False)

    maximum_storage_capacity = forms.IntegerField(min_value=1)
    is_active = forms.BooleanField(required=False)

    def clean(self):
        cleaned_data = super().clean()

        open_time = cleaned_data.get("po_schedule_open")
        close_time = cleaned_data.get("po_schedule_close")
        capacity = cleaned_data.get("maximum_storage_capacity")

        if open_time and close_time and close_time <= open_time:
            self.add_error(
                "po_schedule_close",
                "Closing time must be after opening time."
            )

        if capacity is not None and capacity <= 0:
            self.add_error(
                "maximum_storage_capacity",
                "Maximum storage capacity must be positive."
            )

        return cleaned_data

# ==========================================================
#  DELIVERIES FORMS (SQL-FIRST, NO ORM)
#  Matches david_objects.sql procedures:
#   - sp_create_delivery(... p_weight INT, p_delivery_date TIMESTAMPTZ, ...)
#   - sp_update_delivery(... p_weight INT, p_delivery_date TIMESTAMPTZ, ...)
# ==========================================================

DELIVERY_STATUS_CHOICES = [
    ("registered", "Registered"),
    ("ready", "Ready"),
    ("pending", "Pending"),
    ("in_transit", "In transit"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
    # ("delayed", "Delayed"),  # only keep if your DB allows it (your workflow doesn't mention it)
]

DELIVERY_PRIORITY_CHOICES = [
    ("low", "Low"),
    ("normal", "Normal"),
    ("high", "High"),
    ("urgent", "Urgent"),
]


class DeliveryCreateForm(forms.Form):
    # --- FKs / references (IDs) ---
    driver_id = forms.IntegerField(required=False, min_value=1, label="Driver ID")
    route_id = forms.IntegerField(required=False, min_value=1, label="Route ID")
    inv_id = forms.IntegerField(required=False, min_value=1, label="Invoice ID")
    client_id = forms.IntegerField(required=False, min_value=1, label="Client ID")
    war_id = forms.IntegerField(required=False, min_value=1, label="Warehouse ID")

    # --- delivery basic fields ---
    tracking_number = forms.CharField(required=False, max_length=50, label="Tracking number")
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Description")

    # --- sender ---
    sender_name = forms.CharField(required=False, max_length=100, label="Sender name")
    sender_address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Sender address")
    sender_phone = forms.CharField(required=False, max_length=20, label="Sender phone")
    sender_email = forms.EmailField(required=False, label="Sender email")

    # --- recipient ---
    recipient_name = forms.CharField(required=False, max_length=100, label="Recipient name")
    recipient_address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Recipient address")
    recipient_phone = forms.CharField(required=False, max_length=20, label="Recipient phone")
    recipient_email = forms.EmailField(required=False, label="Recipient email")

    # --- package ---
    item_type = forms.CharField(required=False, max_length=20, label="Item type")

    # DB/SP expect INT and SP enforces >= 1 if provided
    weight = forms.IntegerField(required=False, min_value=1, label="Weight")

    dimensions = forms.CharField(required=False, max_length=50, label="Dimensions")

    # --- status / priority / dates ---
    # In DB sp_create_delivery default is 'registered' if you pass NULL
    status = forms.ChoiceField(required=False, choices=DELIVERY_STATUS_CHOICES, initial="registered", label="Status")
    priority = forms.ChoiceField(required=False, choices=DELIVERY_PRIORITY_CHOICES, initial="normal", label="Priority")

    # DB expects TIMESTAMPTZ. Your template currently uses <input type="date">,
    # so accept both date-only and datetime-local formats.
    delivery_date = forms.DateTimeField(
        required=False,
        input_formats=[
            "%Y-%m-%d",          # from <input type="date">
            "%Y-%m-%dT%H:%M",    # from <input type="datetime-local">
            "%Y-%m-%d %H:%M:%S",
        ],
        label="Delivery date",
    )


class DeliveryEditForm(forms.Form):
    # same as update SP fields (no status here)
    driver_id = forms.IntegerField(required=False, min_value=1, label="Driver ID")
    route_id = forms.IntegerField(required=False, min_value=1, label="Route ID")
    inv_id = forms.IntegerField(required=False, min_value=1, label="Invoice ID")
    client_id = forms.IntegerField(required=False, min_value=1, label="Client ID")
    war_id = forms.IntegerField(required=False, min_value=1, label="Warehouse ID")

    tracking_number = forms.CharField(required=False, max_length=50, label="Tracking number")
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Description")

    sender_name = forms.CharField(required=False, max_length=100, label="Sender name")
    sender_address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Sender address")
    sender_phone = forms.CharField(required=False, max_length=20, label="Sender phone")
    sender_email = forms.EmailField(required=False, label="Sender email")

    recipient_name = forms.CharField(required=False, max_length=100, label="Recipient name")
    recipient_address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Recipient address")
    recipient_phone = forms.CharField(required=False, max_length=20, label="Recipient phone")
    recipient_email = forms.EmailField(required=False, label="Recipient email")

    item_type = forms.CharField(required=False, max_length=20, label="Item type")
    weight = forms.IntegerField(required=False, min_value=1, label="Weight")
    dimensions = forms.CharField(required=False, max_length=50, label="Dimensions")

    priority = forms.ChoiceField(required=False, choices=DELIVERY_PRIORITY_CHOICES, label="Priority")
    in_transition = forms.BooleanField(required=False, label="In transition")

    delivery_date = forms.DateTimeField(
        required=False,
        input_formats=[
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
        ],
        label="Delivery date",
    )


class DeliveryStatusUpdateForm(forms.Form):
    status = forms.ChoiceField(choices=DELIVERY_STATUS_CHOICES, label="Status")
    staff_id = forms.IntegerField(required=False, min_value=1, label="Staff ID")
    warehouse_id = forms.IntegerField(required=False, min_value=1, label="Warehouse ID")
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Notes")


class DeliveryImportJSONForm(forms.Form):
    file = forms.FileField(label="JSON file")
