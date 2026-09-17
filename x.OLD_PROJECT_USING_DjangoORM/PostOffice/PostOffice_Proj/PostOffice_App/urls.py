"""
URL configuration for the Post Office application.
This module maps URL patterns to the split view modules.
"""

from django.urls import path
from .views import (
    core,
    dashboard,
    auth_views,
    users,
    warehouses,
    vehicles,
    routes,
    deliveries,
    invoices,
    notifications,
)

urlpatterns = [
    # Dashboard / Home
    path("", dashboard.dashboard, name="dashboard"),
    path("home/", core.home, name="home"),

    # Authentication
    path("login/", auth_views.login_view, name="login"),
    path("register/", auth_views.register_view, name="register"),
    path("logout/", auth_views.logout_view, name="logout"),

    # User profile
    path("profile/", users.client_profile, name="client_profile"),

    # Warehouses
    path("warehouses/", warehouses.warehouses_list, name="warehouses_list"),
    path("warehouses/create/", warehouses.warehouses_create, name="warehouses_create"),
    path("warehouses/<int:warehouse_id>/edit/", warehouses.warehouses_edit, name="warehouses_edit"),
    path("warehouses/<int:warehouse_id>/delete/", warehouses.warehouses_delete, name="warehouses_delete"),
    path("warehouses/import/json/", warehouses.warehouses_import_json, name="warehouses_import_json"),
    path("warehouses/export/json/", warehouses.warehouses_export_json, name="warehouses_export_json"),
    path("warehouses/export/csv/", warehouses.warehouses_export_csv, name="warehouses_export_csv"),

    # Vehicles
    path("vehicles/", vehicles.vehicles_list, name="vehicles_list"),
    path("vehicles/create/", vehicles.vehicles_create, name="vehicles_create"),
    path("vehicles/<int:vehicle_id>/edit/", vehicles.vehicles_edit, name="vehicles_edit"),
    path("vehicles/<int:vehicle_id>/delete/", vehicles.vehicles_delete, name="vehicles_delete"),
    path("vehicles/import/json/", vehicles.vehicles_import_json, name="vehicles_import_json"),
    path("vehicles/export/json/", vehicles.vehicles_export_json, name="vehicles_export_json"),
    path("vehicles/export/csv/", vehicles.vehicles_export_csv, name="vehicles_export_csv"),

    # Routes
    path("routes/", routes.routes_list, name="routes_list"),
    path("routes/create/", routes.routes_create, name="routes_create"),
    path("routes/<int:route_id>/edit/", routes.routes_edit, name="routes_edit"),
    path("routes/<int:route_id>/delete/", routes.routes_delete, name="routes_delete"),
    path("routes/import/json/", routes.routes_import_json, name="routes_import_json"),
    path("routes/export/json/", routes.routes_export_json, name="routes_export_json"),
    path("routes/export/csv/", routes.routes_export_csv, name="routes_export_csv"),

    # Deliveries
    path("deliveries/", deliveries.deliveries_list, name="deliveries_list"),
    path("deliveries/create/", deliveries.deliveries_create, name="deliveries_create"),
    path("deliveries/<int:delivery_id>/", deliveries.deliveries_detail, name="deliveries_detail"),
    path("deliveries/<int:delivery_id>/edit/", deliveries.deliveries_edit, name="deliveries_edit"),
    path("deliveries/<int:delivery_id>/delete/", deliveries.deliveries_delete, name="deliveries_delete"),
    path("deliveries/import/json/", deliveries.deliveries_import_json, name="deliveries_import_json"),
    path("deliveries/export/json/", deliveries.deliveries_export_json, name="deliveries_export_json"),
    path("deliveries/export/csv/", deliveries.deliveries_export_csv, name="deliveries_export_csv"),

    # Invoices
    path("invoices/", invoices.invoice_list, name="invoice_list"),
    path("invoices/create/", invoices.invoice_create, name="invoice_create"),
    path("invoices/<int:invoice_id>/edit/", invoices.invoice_edit, name="invoice_edit"),
    path("invoices/<int:invoice_id>/delete/", invoices.invoice_delete, name="invoice_delete"),
    path("invoices/import/json/", invoices.invoices_import_json, name="invoices_import_json"),
    path("invoices/export/json/", invoices.invoices_export_json, name="invoices_export_json"),
    path("invoices/export/csv/", invoices.invoices_export_csv, name="invoices_export_csv"),
    path("invoices/export/pdf/", invoices.invoices_export_pdf, name="invoices_export_pdf"),

    # Users / Clients (admin)
    path("users/", users.users_list, name="users_list"),
    path("users/create/", users.users_form, name="users_create"),
    path("users/<int:user_id>/edit/", users.users_form, name="users_edit"),

    path("clients/", users.clients_list, name="clients_list"),
    path("clients/create/", users.clients_form, name="clients_create"),
    path("clients/<int:user_id>/edit/", users.clients_form, name="clients_edit"),

    # Notifications (MongoDB)
    path("notifications/", notifications.get_notifications, name="get_notifications"),
    path("notifications/read/<str:notif_id>/", notifications.mark_notification_read, name="mark_notification_read"),
]
