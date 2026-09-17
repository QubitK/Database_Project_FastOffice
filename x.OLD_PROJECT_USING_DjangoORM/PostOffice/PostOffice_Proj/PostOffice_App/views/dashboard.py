# ==========================================================
#  DASHBOARD
# ==========================================================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ..models import (
    User,
    Employee,
    Vehicle,
    Invoice,
    Route,
    Delivery,
)


@login_required
def dashboard(request):
    role = request.user.role

    if role == "admin":
        stats = {
            "total_vehicles": Vehicle.objects.count(),
            "total_deliveries": Delivery.objects.count(),
            "total_clients": User.objects.filter(role="client").count(),
            "total_employees": Employee.objects.count(),
            "active_routes": Route.objects.exclude(delivery_status__in=["Completed", "Cancelled"]).count(),
            "pending_deliveries": Delivery.objects.filter(status="Pending").count(),
            "total_invoices": Invoice.objects.count(),
        }
    elif role == "driver":
        employee = getattr(request.user, "employee", None)
        my_deliveries = Delivery.objects.filter(driver=employee) if employee else Delivery.objects.none()
        stats = {"my_deliveries": my_deliveries}
    else:  # client, staff, manager
        stats = {"my_deliveries": Delivery.objects.filter(client=request.user)}

    return render(request, "dashboard/admin.html", {"stats": stats, "role": role})