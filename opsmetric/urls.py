"""URL configuration for opsmetric project."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import include, path


def admin_guard(request):
    """Redirect non-superusers to a styled 403 page."""
    if request.user.is_authenticated and not request.user.is_superuser:
        return render(request, "403.html", status=403)
    return redirect("/admin/")


urlpatterns = [
    path("admin-access/", admin_guard, name="admin_access"),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("monitoring.urls")),
]
