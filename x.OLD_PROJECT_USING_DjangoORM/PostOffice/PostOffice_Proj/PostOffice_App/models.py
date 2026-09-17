from django.db import models
from django.contrib.auth.models import AbstractUser
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django import forms
from django.db.models import F
# ==========================================================
#  USER & EMPLOYEE HIERARCHY (replaces Mongo "users")
#  - Keeps role-based logic from views2.py
#  - Respects Employee / Driver / Staff pattern from views1.py
# ==========================================================

class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("client", "Client"),
        ("driver", "Driver"),
        ("staff", "Staff"),
        ("manager", "Manager"),
    ]

    # Extra profile fields from Mongo users.json
    full_name = models.CharField(max_length=150, blank=True)   # "name" in Mongo
    contact = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="client")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # password hash is handled by Django; we do NOT keep psswd_hash

    def __str__(self):
        label = self.full_name or self.username
        return f"{label} ({self.role})"

    class Meta:
        ordering = ["username"]


class Employee(models.Model):
    POSITION_CHOICES = [
        ("Driver", "Driver"),
        ("Staff", "Staff"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee")

    # From Mongo "employee" embedded object
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    schedule = models.CharField(max_length=50, blank=True)  # e.g. "08:00-16:00"
    wage = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    hire_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.position}"

    def clean(self):
        """Ensure the linked user's role matches the employee position."""
        # Only validate if a user is attached
        if self.user_id:
            if self.position == "Driver" and self.user.role != "driver":
                raise ValidationError("Associated user's role must be 'driver' for a driver employee.")
            if self.position == "Staff" and self.user.role != "staff":
                raise ValidationError("Associated user's role must be 'staff' for a staff employee.")

    def save(self, *args, **kwargs):
        # Automatically align the user.role with the employee position
        if self.user_id:
            if self.position == "Driver" and self.user.role != "driver":
                self.user.role = "driver"
                self.user.save(update_fields=["role"])
            elif self.position == "Staff" and self.user.role != "staff":
                self.user.role = "staff"
                self.user.save(update_fields=["role"])
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["user__username"]


class EmployeeDriver(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="driver_info")

    # From Mongo driver_info + views1 EmployeeDriver
    license_number = models.CharField(max_length=50)
    license_category = models.CharField(max_length=10)
    license_expiry_date = models.DateField()
    driving_experience_years = models.IntegerField()
    driver_status = models.CharField(max_length=50)  # e.g. "Available", "OnDuty"

    def __str__(self):
        return f"Driver {self.employee.user}"

    class Meta:
        ordering = ["employee__user__username"]


class EmployeeStaff(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="staff_info")

    # From Mongo staff_info.department
    department = models.CharField(max_length=100)

    def __str__(self):
        return f"Staff {self.employee.user} - {self.department}"

    class Meta:
        ordering = ["employee__user__username"]


# ==========================================================
#  WAREHOUSES (post_office_stores.json → PostgreSQL)
# ==========================================================

class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    contact = models.CharField(max_length=50)
    po_schedule_open = models.TimeField()
    po_schedule_close = models.TimeField()
    maximum_storage_capacity = models.IntegerField(
        validators=[MinValueValidator(1)],
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


# ==========================================================
#  VEHICLES (vehicles.json → PostgreSQL)
# ==========================================================

class Vehicle(models.Model):
    vehicle_type = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=20, unique=True)
    capacity = models.FloatField()
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    vehicle_status = models.CharField(max_length=50)
    year = models.IntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
    )
    fuel_type = models.CharField(max_length=50)
    last_maintenance_date = models.DateField()

    def __str__(self):
        return f"{self.plate_number} - {self.vehicle_type}"

    class Meta:
        ordering = ["plate_number"]


# ==========================================================
#  INVOICES (PostgreSQL DDL you provided)
#  - Adds user FK so we can still tie invoices to users in views
# ==========================================================

class Invoice(models.Model):
    # Match existing table: id_invoice as PK
    id_invoice = models.AutoField(primary_key=True)

    # Optional link to a user (not in original DDL but needed for role-based views)
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoices",
    )

    invoice_status = models.CharField(max_length=20, blank=True)
    invoice_type = models.CharField(max_length=50, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    invoice_datetime = models.DateTimeField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=200, blank=True)
    contact = models.CharField(max_length=50, blank=True)

    def __str__(self):
        # Use the object's primary key via pk property to avoid confusion over id_invoice
        return f"Invoice {self.pk} ({self.invoice_status})"

    class Meta:
        db_table = '"PostOffice_App_invoice"'
        ordering = ["-invoice_datetime", "pk"]
        managed = True

class InvoiceItem(models.Model):
    id_item = models.AutoField(primary_key=True)
    invoice = models.ForeignKey(
        Invoice,
        related_name="items",
        on_delete=models.CASCADE,
        db_column="invoice_id",
    )
    shipment_type = models.CharField(max_length=50)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_speed = models.CharField(max_length=50)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = '"postoffice_app_invoice_items"'
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        # Exclude total_price so Django won't try to insert/update it
        exclude = ['total_price']

# ==========================================================
#  ROUTES (routes.json + logic of views1/views2)
# ==========================================================

class Route(models.Model):
    description = models.TextField()

    # Route / delivery status from Mongo
    delivery_status = models.CharField(max_length=50)

    # Timing & metrics from routes.json
    delivery_date = models.DateField(null=True, blank=True)
    delivery_start_time = models.TimeField(null=True, blank=True)
    delivery_end_time = models.TimeField(null=True, blank=True)
    expected_duration = models.DurationField(null=True, blank=True)
    kms_travelled = models.FloatField(default=0)

    driver_notes = models.TextField(blank=True)

    # Relations
    driver = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="routes",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="routes",
    )

    # Origin / destination flattened (from nested origin/destination)
    origin_name = models.CharField(max_length=200)
    origin_address = models.CharField(max_length=255)
    origin_contact = models.CharField(max_length=50, blank=True)

    destination_name = models.CharField(max_length=200)
    destination_address = models.CharField(max_length=255)
    destination_contact = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Route {self.id} - {self.description}"

    class Meta:
        # Prevent assigning the same driver and vehicle to multiple routes on the same date
        unique_together = [("driver", "vehicle", "delivery_date")]
        ordering = ["delivery_date", "pk"]


# ==========================================================
#  DELIVERIES (deliveries.json + views1/views2 logic)
# ==========================================================

class Delivery(models.Model):
    STATUS_CHOICES = [
        ("Registered", "Registered"),
        ("Ready", "Ready"),
        ("Pending", "Pending"),
        ("In Transit", "In Transit"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("normal", "Normal"),
        ("urgent", "Urgent"),
    ]

    # Link to invoice (invoice_id in Mongo)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deliveries",
    )

    tracking_number = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # Sender (embedded in Mongo)
    sender_name = models.CharField(max_length=100)
    sender_address = models.CharField(max_length=255)
    sender_phone = models.CharField(max_length=50, blank=True)
    sender_email = models.EmailField(blank=True)

    # Recipient (embedded in Mongo)
    recipient_name = models.CharField(max_length=100)
    recipient_address = models.CharField(max_length=255)
    recipient_phone = models.CharField(max_length=50, blank=True)
    recipient_email = models.EmailField(blank=True)

    item_type = models.CharField(max_length=50)
    weight = models.IntegerField(
        help_text="Weight in grams",
        validators=[MinValueValidator(1)],
    )
    dimensions = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")

    registered_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    in_transition = models.BooleanField(default=False)

    # Extra fields used in views2 deliveries_edit
    destination = models.CharField(max_length=255, blank=True)
    delivery_date = models.DateField(null=True, blank=True)

    # Relations: driver, client, route (used for dashboards & profile views)
    driver = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="driver_deliveries",
    )
    client = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="client_deliveries",
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deliveries",
    )

    def __str__(self):
        return f"{self.tracking_number} - {self.status}"

    class Meta:
        ordering = ["-registered_at", "tracking_number"]