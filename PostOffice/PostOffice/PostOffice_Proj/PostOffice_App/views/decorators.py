# ==========================================================
#  ROLE-BASED ACCESS DECORATOR (MERGED VERSION)
# ==========================================================

from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles):
    """
    Restrict access to users whose role is included in allowed_roles.

    Usage:
        @login_required
        @role_required("admin")

        @role_required("admin", "staff")

        @role_required(["admin", "staff"])
    """

    # Allow passing a single list/tuple
    if len(allowed_roles) == 1 and isinstance(allowed_roles[0], (list, tuple, set)):
        allowed_roles = allowed_roles[0]

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # Not authenticated
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to access this page.")
                return redirect("login")

            # Get role (user model first, fallback to session)
            role = getattr(request.user, "role", None) or request.session.get("role")

            if not role:
                return HttpResponseForbidden("No role assigned to this account.")

            # Role not permitted
            if role not in allowed_roles:
                return HttpResponseForbidden("You do not have permission to view this page.")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
