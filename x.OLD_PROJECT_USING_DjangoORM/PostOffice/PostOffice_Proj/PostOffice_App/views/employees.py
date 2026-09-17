# ==========================================================
#  EMPLOYEES
# ==========================================================
from datetime import datetime
from decimal import Decimal
import json
from pyexpat.errors import messages
from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from ..models import Employee, Invoice, User
from ..forms import EmployeeDriverForm, EmployeeForm, EmployeeStaffForm, InvoiceForm
from .decorators import role_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator


@login_required
@role_required(["admin"])
def employees_list(request):
    employees_qs = Employee.objects.select_related("user").all()
    paginator = Paginator(employees_qs, 10)
    page_number = request.GET.get("page")
    employees_page = paginator.get_page(page_number)
    return render(request, "core/employees_list.html", {"employees": employees_page})


@login_required
@role_required(["admin"])
def employees_form(request, employee_id=None):
    if employee_id:
        employee = get_object_or_404(Employee, pk=employee_id)
    else:
        employee = None

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        if not user_id:
            return HttpResponseBadRequest("Missing user selection for employee.")
        user = get_object_or_404(User, pk=user_id)

        if employee is None and user.role in {"admin", "client"}:
            return HttpResponseBadRequest("Selected user cannot become an employee.")
        if employee is None and hasattr(user, "employee"):
            return HttpResponseBadRequest("User is already assigned to an employee record.")
        if employee is not None and employee.user_id != user.pk:
            return HttpResponseBadRequest("User mismatch: cannot reassign existing employee to a different user.")

        if employee is None:
            employee = Employee(user=user)

        old_position = employee.position if employee.pk else None
        emp_form = EmployeeForm(request.POST, instance=employee)

        position = request.POST.get("position")
        driver_form = staff_form = None
        if position == "Driver":
            driver_info = getattr(employee, "driver_info", None)
            driver_form = EmployeeDriverForm(request.POST, instance=driver_info)
        elif position == "Staff":
            staff_info = getattr(employee, "staff_info", None)
            staff_form = EmployeeStaffForm(request.POST, instance=staff_info)

        forms_valid = emp_form.is_valid()
        if driver_form:
            forms_valid = forms_valid and driver_form.is_valid()
        if staff_form:
            forms_valid = forms_valid and staff_form.is_valid()

        if forms_valid:
            saved_employee = emp_form.save()

            if old_position and old_position != position:
                try:
                    if old_position == "Driver" and hasattr(saved_employee, "driver_info"):
                        saved_employee.driver_info.delete()
                    if old_position == "Staff" and hasattr(saved_employee, "staff_info"):
                        saved_employee.staff_info.delete()
                except Exception:
                    pass

            if position == "Driver" and driver_form:
                driver_model = driver_form.save(commit=False)
                driver_model.employee = saved_employee
                driver_model.save()
                saved_employee.user.role = "driver"
                saved_employee.user.save(update_fields=["role"])
            elif position == "Staff" and staff_form:
                staff_model = staff_form.save(commit=False)
                staff_model.employee = saved_employee
                staff_model.save()
                saved_employee.user.role = "staff"
                saved_employee.user.save(update_fields=["role"])

            return redirect("employees_list")
    else:
        emp_form = EmployeeForm(instance=employee)
        driver_info = getattr(employee, "driver_info", None) if employee else None
        staff_info = getattr(employee, "staff_info", None) if employee else None

        driver_form = EmployeeDriverForm(instance=driver_info) if driver_info else EmployeeDriverForm()
        staff_form = EmployeeStaffForm(instance=staff_info) if staff_info else EmployeeStaffForm()

    return render(
        request,
        "core/employees_form.html",
        {
            "employee_form": emp_form,
            "driver_form": driver_form,
            "staff_form": staff_form,
            "employee": employee,
        },
    )