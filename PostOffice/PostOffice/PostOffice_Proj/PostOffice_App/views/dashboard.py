from django.db import connection, transaction
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


# ==========================================================
# DASHBOARD — No ORM, uses DB objects only
# ==========================================================
@login_required
def dashboard(request):
    role = request.user.role

    # Fetch stats from DB function
    with connection.cursor() as cur:
        cur.execute("SELECT * FROM fn_get_dashboard_stats(%s, %s)", [request.user.id, role])
        stats = {row[0]: row[1] for row in cur.fetchall()}

    return render(request, "dashboard/admin.html", {"stats": stats, "role": role})


# ==========================================================
# EMPLOYEES
# ==========================================================

def employees_list(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM v_employees_full;")
        columns = [col[0] for col in cursor.description]
        employees = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, "employees/list.html", {"employees": employees})


def employees_create(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL sp_create_employee(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);",
                        [
                            request.POST.get("username"),
                            request.POST.get("email"),
                            make_password(request.POST.get("password")),
                            request.POST.get("first_name"),
                            request.POST.get("last_name"),
                            request.POST.get("contact"),
                            request.POST.get("address"),
                            request.POST.get("war_id"),
                            request.POST.get("emp_position"),
                            request.POST.get("schedule"),
                            request.POST.get("wage"),
                            request.POST.get("hire_date"),
                            request.POST.get("license_number"),
                            request.POST.get("license_category"),
                            request.POST.get("license_expiry"),
                            request.POST.get("driving_experience"),
                            request.POST.get("driver_status"),
                            request.POST.get("department"),
                            None
                        ]
                    )

            messages.success(request, "Employee created successfully.")
            return redirect("employees_list")
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "employees/create.html")


def employees_update(request, employee_id):
    if request.method == "POST":
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL sp_update_employee(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);",
                        [
                            employee_id,
                            request.POST.get("email"),
                            request.POST.get("first_name"),
                            request.POST.get("last_name"),
                            request.POST.get("contact"),
                            request.POST.get("address"),
                            request.POST.get("war_id"),
                            request.POST.get("emp_position"),
                            request.POST.get("schedule"),
                            request.POST.get("wage"),
                            request.POST.get("is_active"),
                            request.POST.get("license_number"),
                            request.POST.get("license_category"),
                            request.POST.get("license_expiry"),
                            request.POST.get("driving_experience"),
                            request.POST.get("driver_status"),
                            request.POST.get("department"),
                        ]
                    )

            messages.success(request, "Employee updated successfully.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("employees_list")


def employees_delete(request, employee_id):
    if request.method == "POST":
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("CALL sp_delete_employee(%s);", [employee_id])
            messages.success(request, "Employee deleted successfully.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("employees_list")


# ==========================================================
# CLIENTS
# ==========================================================

@login_required
def clients_list(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM v_clients;")
        columns = [col[0].lower() for col in cursor.description]  # lowercase
        clients = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, "clients/list.html", {"clients": clients})

@login_required
def clients_create(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                p_id = None
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL sp_create_user(%s,%s,%s,%s,%s,%s,%s,%s,%s);",
                        [
                            request.POST.get("username"),
                            request.POST.get("email"),
                            make_password(request.POST.get("password")),
                            request.POST.get("first_name"),
                            request.POST.get("last_name"),
                            request.POST.get("contact"),
                            request.POST.get("address"),
                            "client",  # role
                            p_id       # INOUT id
                        ]
                    )
            messages.success(request, "Client created successfully.")
            return redirect("clients_list")
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "clients/create.html")


@login_required
def clients_update(request, client_id):
    if request.method == "POST":
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CALL sp_update_user(%s,%s,%s,%s,%s,%s,%s,%s);",
                        [
                            client_id,
                            request.POST.get("email"),
                            request.POST.get("first_name"),
                            request.POST.get("last_name"),
                            request.POST.get("contact"),
                            request.POST.get("address"),
                            None,  # role stays same
                            request.POST.get("is_active") == "true"
                        ]
                    )
            messages.success(request, "Client updated successfully.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("clients_list")


@login_required
def clients_delete(request, client_id):
    if request.method == "POST":
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("CALL sp_delete_user(%s);", [client_id])
            messages.success(request, "Client deleted successfully.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("clients_list")
