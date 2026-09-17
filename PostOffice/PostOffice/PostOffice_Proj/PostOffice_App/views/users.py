# # ==========================================================
# #  USER & CLIENT MANAGEMENT
# # ==========================================================
# import json
# from pyexpat.errors import messages
# from django.db import connection
# from django.shortcuts import render, get_object_or_404, redirect
# from ..models import Delivery, User
# from ..forms import CustomUserChangeForm, CustomUserCreationForm
# from .decorators import role_required
# from django.contrib.auth.decorators import login_required
# from django.core.paginator import Paginator
from django.db import connection
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password

from ..forms import UserForm
from .decorators import role_required


# # ==========================================================
# #  ADMIN PROFILE
# # ==========================================================
# @login_required
# @role_required(["admin"])
# def users_list(request):
#     users = User.objects.all().order_by("username")
#     paginator = Paginator(users, 10)
#     page_number = request.GET.get("page")
#     users_page = paginator.get_page(page_number)
#     return render(request, "core/users_list.html", {"users": users_page})




@login_required
@role_required(["admin"])
def users_list(request):
    """
    Admin-only list of all system users.
    Data is read from SQL VIEW v_users_admin.
    """

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM v_users_admin")
        columns = [col[0] for col in cursor.description]
        users = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(
        request,
        "core/users_list.html",
        {"users": users},
    )


# @login_required
# @role_required(["admin"])
# def users_form(request, user_id=None):
#     if user_id:
#         user = get_object_or_404(User, pk=user_id)
#         FormClass = CustomUserChangeForm
#     else:
#         user = None
#         FormClass = CustomUserCreationForm

#     if request.method == "POST":
#         form = FormClass(request.POST, instance=user)
#         if form.is_valid():
#             form.save()
#             return redirect("users_list")
#     else:
#         form = FormClass(instance=user)

#     return render(request, "core/users_form.html", {"form": form})





@login_required
@role_required(["admin"])
def users_form(request, user_id=None):
    """
    Create or edit a generic USER (admin / manager / client).
    Uses stored procedures instead of ORM.
    """

    is_edit = user_id is not None

    if request.method == "POST":
        form = UserForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data

            with connection.cursor() as cursor:
                if is_edit:
                    # =========================
                    # UPDATE EXISTING USER
                    # =========================
                    cursor.execute(
                        """
                        CALL sp_update_user(
                            %s,  -- id
                            %s,  -- email
                            %s,  -- first_name
                            %s,  -- last_name
                            %s,  -- contact
                            %s,  -- address
                            %s,  -- role
                            %s   -- is_active
                        )
                        """,
                        [
                            user_id,
                            cd["email"],
                            cd["first_name"],
                            cd["last_name"],
                            cd["contact"],
                            cd["address"],
                            cd["role"],
                            cd.get("is_active", False),
                        ],
                    )
                else:
                    # =========================
                    # CREATE NEW USER
                    # =========================
                    cursor.execute(
                        """
                        CALL sp_create_user(
                            %s,  -- username
                            %s,  -- email
                            %s,  -- password
                            %s,  -- first_name
                            %s,  -- last_name
                            %s,  -- contact
                            %s,  -- address
                            %s   -- role
                        )
                        """,
                        [
                            cd["username"],
                            cd["email"],
                            make_password(cd["password"]),
                            cd["first_name"],
                            cd["last_name"],
                            cd["contact"],
                            cd["address"],
                            cd["role"],
                        ],
                    )

            return redirect("users_list")

    else:
        form = UserForm()

    return render(
        request,
        "core/users_form.html",
        {
            "form": form,
            "is_edit": is_edit,
        },
    )



# @login_required
# @role_required(["admin"])
# def clients_list(request):
#     clients_qs = User.objects.filter(role="client").order_by("username")
#     paginator = Paginator(clients_qs, 10)
#     page_number = request.GET.get("page")
#     clients_page = paginator.get_page(page_number)
#     return render(request, "core/clients.html", {"clients": clients_page})




@login_required
@role_required(["admin"])
def clients_list(request):
    """
    Admin-only list of clients using v_clients view.
    """

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM v_clients
        """)
        columns = [col[0] for col in cursor.description]
        clients = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(
        request,
        "core/clients.html",
        {"clients": clients},
    )

# @login_required
# @role_required(["admin"])
# def clients_form(request, user_id=None):
#     if user_id:
#         user = get_object_or_404(User, pk=user_id, role="client")
#         FormClass = CustomUserChangeForm
#     else:
#         user = None
#         FormClass = CustomUserCreationForm

#     if request.method == "POST":
#         form = FormClass(request.POST, instance=user)
#         if form.is_valid():
#             client = form.save(commit=False)
#             client.role = "client"
#             client.save()
#             return redirect("clients_list")
#     else:
#         form = FormClass(instance=user)

#     return render(request, "core/clients_form.html", {"form": form})





@login_required
@role_required(["admin"])
def clients_form(request, user_id=None):
    """
    Create or edit a CLIENT user.
    Role is always 'client'.
    Client table row is handled automatically by sp_create_user.
    """

    is_edit = user_id is not None

    if request.method == "POST":
        form = UserForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data

            with connection.cursor() as cursor:
                if is_edit:
                    # UPDATE existing client
                    cursor.execute(
                        """
                        CALL sp_update_user(
                            %s,  -- id
                            %s,  -- email
                            %s,  -- first_name
                            %s,  -- last_name
                            %s,  -- contact
                            %s,  -- address
                            %s,  -- role
                            %s   -- is_active
                        )
                        """,
                        [
                            user_id,
                            cd["email"],
                            cd["first_name"],
                            cd["last_name"],
                            cd["contact"],
                            cd["address"],
                            "client",
                            cd["is_active"],
                        ],
                    )
                else:
                    # CREATE new client
                    cursor.execute(
                        """
                        CALL sp_create_user(
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        [
                            cd["username"],
                            cd["email"],
                            make_password(cd["password"]),
                            cd["first_name"],
                            cd["last_name"],
                            cd["contact"],
                            cd["address"],
                            "client",
                        ],
                    )

            return redirect("clients_list")

    else:
        form = UserForm()

    return render(
        request,
        "core/clients_form.html",
        {
            "form": form,
            "is_edit": is_edit,
        },
    )



# # ==========================================================
# #  CLIENT PROFILE
# # ==========================================================
# @login_required
# @role_required(["client", "admin"])
# def client_profile(request):
#     if request.user.role == "client":
#         my_deliveries = Delivery.objects.filter(client=request.user)
#         user_obj = request.user
#     else:
#         my_deliveries = Delivery.objects.none()
#         user_obj = request.user

#     return render(
#         request,
#         "clients/profile.html",
#         {"deliveries": my_deliveries, "user": user_obj},
#     )




@login_required
@role_required(["client", "admin"])
def client_profile(request):
    """
    Client profile page.
    If the logged user is a client, retrieves their deliveries
    using fn_get_client_deliveries().
    """

    user_obj = request.user
    deliveries = []

    if request.user.role == "client":
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM fn_get_client_deliveries(%s)
                """,
                [request.user.id],
            )

            columns = [col[0] for col in cursor.description]
            deliveries = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(
        request,
        "clients/profile.html",
        {
            "user": user_obj,
            "deliveries": deliveries,
        },
    )
