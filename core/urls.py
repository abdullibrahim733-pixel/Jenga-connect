from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("hardware-stores/", views.hardware_shops, name="hardware_shops"),
    path("product/<uuid:pk>/", views.product_detail, name="product_detail"),
    path("login/", views.user_login, name="login"),
    path("register/", views.register, name="register"),
    path("logout/", views.user_logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/sales-metrics/", views.sales_metrics, name="sales_metrics"),
    path("hardware/add-product/", views.add_product, name="add_product"),
    path(
        "hardware/order/<uuid:order_id>/<str:action>/",
        views.manage_order,
        name="manage_order",
    ),
    path(
        "hardware/product/<uuid:product_id>/delete/",
        views.delete_product,
        name="delete_product",
    ),
    path("manage/", views.manage_page, name="manage_page"),
    path("checkout/", views.checkout, name="checkout"),
    path(
        "payment/initiate/<uuid:order_id>/",
        views.initiate_payment,
        name="initiate_payment",
    ),
    path(
        "payment/status/<uuid:payment_id>/", views.payment_status, name="payment_status"
    ),
    path("map/", views.map_view, name="map_view"),
    path("notifications/", views.notifications_view, name="notifications"),
    path(
        "notifications/<uuid:notification_id>/read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "notifications/read-all/",
        views.mark_all_notifications_read,
        name="mark_all_notifications_read",
    ),
]
