# ==========================================================
#  AUTH VIEWS (login / register / logout)
# ==========================================================
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect
from django.contrib import messages
from ..forms import CustomUserCreationForm



def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            request.session["role"] = user.role
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "auth/login.html")


def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = CustomUserCreationForm()
    return render(request, "auth/register.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    request.session.flush()
    return redirect("login")