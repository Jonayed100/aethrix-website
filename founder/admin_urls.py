"""Admin dashboard: orders only, for your team admins (and you). Lives at the secret ADMIN_PANEL_URL."""
from django.urls import path

from accounts.views import admin_login_view

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("login/", admin_login_view, name="login"),
    path("", views.overview, name="overview"),
    path("orders/", views.orders, name="orders"),
    path("orders/<str:reference>/", views.order_detail, name="order"),
    path("orders/<str:reference>/message/", views.order_message, name="order_message"),
    path("orders/<str:reference>/invite/", views.order_invite, name="order_invite"),
    path("account/", views.account, name="account"),
]
