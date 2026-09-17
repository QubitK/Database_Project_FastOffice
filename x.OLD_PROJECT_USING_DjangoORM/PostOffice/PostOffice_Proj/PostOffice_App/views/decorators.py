# ==========================================================
#  ROLE-BASED ACCESS DECORATOR
# ==========================================================

from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

def role_required(allowed_roles):
    """
    Restrict access to users whose User.role is in allowed_roles.
    Example: @login_required @role_required(["admin", "client"])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")

            if request.user.role not in allowed_roles:
                return HttpResponseForbidden("You do not have permission to view this page.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator