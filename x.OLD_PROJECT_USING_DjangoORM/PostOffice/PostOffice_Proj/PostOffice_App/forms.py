from django import forms
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    InvoiceItem, User, Employee, EmployeeDriver, EmployeeStaff,
    Warehouse, Vehicle, Invoice, Route, Delivery
)


# ==========================================================
#  USER FORMS
# ==========================================================

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            "username", "full_name", "email", "contact", "address",
            "tax_id", "role", "password1", "password2"
        ]


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = [
            "username", "full_name", "email", "contact", "address",
            "tax_id", "role"
        ]


# ==========================================================
#  EMPLOYEE FORMS (Driver / Staff specialization)
# ==========================================================

class EmployeeForm(forms.ModelForm):
    # Expose the related user so the user assignment can be handled via the form
    user = forms.ModelChoiceField(
        queryset=User.objects.exclude(role__in=["admin", "client"]),
        required=True,
        label="User",
    )

    class Meta:
        model = Employee
        fields = [
            "user", "position", "schedule", "wage",
            "is_active", "hire_date"
        ]
        widgets = {
            "hire_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_user(self):
        user = self.cleaned_data.get("user")
        # Ensure the selected user does not already have an employee record
        if user and hasattr(user, "employee") and (not self.instance.pk or user.employee.pk != self.instance.pk):
            raise forms.ValidationError("This user is already assigned to an employee record.")
        return user

    def clean_wage(self):
        wage = self.cleaned_data.get("wage")
        if wage is not None and wage < 0:
            raise forms.ValidationError("Wage must be a positive number.")
        return wage


class EmployeeDriverForm(forms.ModelForm):
    class Meta:
        model = EmployeeDriver
        fields = [
            "license_number", "license_category",
            "license_expiry_date", "driving_experience_years",
            "driver_status"
        ]
        widgets = {
            "license_expiry_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        expiry = cleaned_data.get("license_expiry_date")
        experience = cleaned_data.get("driving_experience_years")
        if expiry and expiry <= timezone.now().date():
            self.add_error("license_expiry_date", "License expiry date must be in the future.")
        if experience is not None and experience < 0:
            self.add_error("driving_experience_years", "Driving experience must be non-negative.")
        return cleaned_data


class EmployeeStaffForm(forms.ModelForm):
    class Meta:
        model = EmployeeStaff
        fields = [
            "department"
        ]


# ==========================================================
#  WAREHOUSE FORM
# ==========================================================

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = [
            "name", "address", "contact",
            "po_schedule_open", "po_schedule_close",
            "maximum_storage_capacity"
        ]
        widgets = {
            # Provide time pickers for schedule fields
            "po_schedule_open": forms.TimeInput(attrs={"type": "time"}),
            "po_schedule_close": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        open_time = cleaned_data.get("po_schedule_open")
        close_time = cleaned_data.get("po_schedule_close")
        capacity = cleaned_data.get("maximum_storage_capacity")
        if open_time and close_time and close_time <= open_time:
            self.add_error("po_schedule_close", "Closing time must be after opening time.")
        if capacity is not None and capacity <= 0:
            self.add_error("maximum_storage_capacity", "Maximum storage capacity must be positive.")
        return cleaned_data


# ==========================================================
#  VEHICLE FORM
# ==========================================================

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "vehicle_type", "plate_number", "capacity",
            "brand", "model", "vehicle_status",
            "year", "fuel_type", "last_maintenance_date"
        ]
        widgets = {
            "last_maintenance_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")
        if capacity is not None and capacity <= 0:
            raise forms.ValidationError("Capacity must be a positive number.")
        return capacity

    def clean_year(self):
        year = self.cleaned_data.get("year")
        if year is not None and (year < 1900 or year > 2100):
            raise forms.ValidationError("Year must be between 1900 and 2100.")
        return year


# ==========================================================
#  INVOICE FORM
# ==========================================================

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "user", "invoice_status", "invoice_type",
            "quantity", "invoice_datetime", "cost",
            "paid", "payment_method",
            "name", "address", "contact",
        ]
        widgets = {
            "invoice_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["shipment_type", "weight", "delivery_speed", "quantity", "unit_price", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


# ==========================================================
#  ROUTE FORM
# ==========================================================

class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = [
            "description", "delivery_status",
            "delivery_date", "delivery_start_time",
            "delivery_end_time", "expected_duration",
            "kms_travelled", "driver_notes",
            "driver", "vehicle",
            "origin_name", "origin_address", "origin_contact",
            "destination_name", "destination_address", "destination_contact"
        ]
        widgets = {
            "delivery_date": forms.DateInput(attrs={"type": "date"}),
            "delivery_start_time": forms.TimeInput(attrs={"type": "time"}),
            "delivery_end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("delivery_start_time")
        end = cleaned_data.get("delivery_end_time")
        duration = cleaned_data.get("expected_duration")
        if start and end and end <= start:
            self.add_error("delivery_end_time", "End time must be after start time.")
        if duration is not None and duration.total_seconds() <= 0:
            self.add_error("expected_duration", "Expected duration must be positive.")
        return cleaned_data


# ==========================================================
#  DELIVERY FORM
# ==========================================================

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = [
            "invoice",
            "tracking_number", "description",

            # SENDER
            "sender_name", "sender_address",
            "sender_phone", "sender_email",

            # RECIPIENT
            "recipient_name", "recipient_address",
            "recipient_phone", "recipient_email",

            "item_type", "weight", "dimensions",

            "status", "priority",
            "registered_at", "updated_at",
            "in_transition",

            "destination", "delivery_date",

            "driver", "client", "route"
        ]
        widgets = {
            "registered_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "updated_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "delivery_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        weight = cleaned_data.get("weight")
        registered = cleaned_data.get("registered_at")
        updated = cleaned_data.get("updated_at")
        if weight is not None and weight <= 0:
            self.add_error("weight", "Weight must be a positive number.")
        if registered and updated and updated <= registered:
            self.add_error("updated_at", "Updated time must be after registered time.")
        return cleaned_data


class VehicleImportForm(forms.Form):
    file = forms.FileField(label="Select JSON file")


class WarehouseImportForm(forms.Form):
    file = forms.FileField()


class DeliveryImportForm(forms.Form):
    file = forms.FileField()

class RouteImportForm(forms.Form):
    file = forms.FileField()