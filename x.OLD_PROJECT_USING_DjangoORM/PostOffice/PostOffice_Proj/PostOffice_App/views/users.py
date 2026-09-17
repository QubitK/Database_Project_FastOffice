# ==========================================================
#  USER & CLIENT MANAGEMENT
# ==========================================================
import json
from pyexpat.errors import messages
from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from ..models import Delivery, User
from ..forms import CustomUserChangeForm, CustomUserCreationForm
from .decorators import role_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

# ==========================================================
#  ADMIN PROFILE
# ==========================================================
@login_required
@role_required(["admin"])
def users_list(request):
    users = User.objects.all().order_by("username")
    paginator = Paginator(users, 10)
    page_number = request.GET.get("page")
    users_page = paginator.get_page(page_number)
    return render(request, "core/users_list.html", {"users": users_page})


@login_required
@role_required(["admin"])
def users_form(request, user_id=None):
    if user_id:
        user = get_object_or_404(User, pk=user_id)
        FormClass = CustomUserChangeForm
    else:
        user = None
        FormClass = CustomUserCreationForm

    if request.method == "POST":
        form = FormClass(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("users_list")
    else:
        form = FormClass(instance=user)

    return render(request, "core/users_form.html", {"form": form})


@login_required
@role_required(["admin"])
def clients_list(request):
    clients_qs = User.objects.filter(role="client").order_by("username")
    paginator = Paginator(clients_qs, 10)
    page_number = request.GET.get("page")
    clients_page = paginator.get_page(page_number)
    return render(request, "core/clients.html", {"clients": clients_page})


@login_required
@role_required(["admin"])
def clients_form(request, user_id=None):
    if user_id:
        user = get_object_or_404(User, pk=user_id, role="client")
        FormClass = CustomUserChangeForm
    else:
        user = None
        FormClass = CustomUserCreationForm

    if request.method == "POST":
        form = FormClass(request.POST, instance=user)
        if form.is_valid():
            client = form.save(commit=False)
            client.role = "client"
            client.save()
            return redirect("clients_list")
    else:
        form = FormClass(instance=user)

    return render(request, "core/clients_form.html", {"form": form})

# ==========================================================
#  CLIENT PROFILE
# ==========================================================
@login_required
@role_required(["client", "admin"])
def client_profile(request):
    if request.user.role == "client":
        my_deliveries = Delivery.objects.filter(client=request.user)
        user_obj = request.user
    else:
        my_deliveries = Delivery.objects.none()
        user_obj = request.user

    return render(
        request,
        "clients/profile.html",
        {"deliveries": my_deliveries, "user": user_obj},
    )