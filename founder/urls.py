"""Founder dashboard: everything. Lives at the secret FOUNDER_URL."""
from django.urls import path

from accounts.views import founder_login_view

from . import views

app_name = "founder"

urlpatterns = [
    path("login/", founder_login_view, name="login"),
    path("", views.overview, name="overview"),
    path("orders/", views.orders, name="orders"),
    path("orders/export.csv", views.orders_csv, name="orders_csv"),
    path("orders/<str:reference>/", views.order_detail, name="order"),
    path("orders/<str:reference>/message/", views.order_message, name="order_message"),
    path("orders/<str:reference>/invite/", views.order_invite, name="order_invite"),
    path("projects/", views.projects, name="projects"),
    path("projects/new/", views.project_edit, name="project_add"),
    path("projects/<int:pk>/edit/", views.project_edit, name="project_edit"),
    path("projects/<int:pk>/delete/", views.project_delete, name="project_delete"),
    path("projects/<int:pk>/toggle/", views.project_toggle, name="project_toggle"),
    path("clients/", views.clients, name="clients"),
    path("clients/<int:pk>/", views.client_detail, name="client"),
    path("team/", views.team, name="team"),
    path("team/<int:pk>/", views.team_member, name="team_member"),
    path("team/<int:pk>/toggle/", views.team_toggle, name="team_toggle"),
    path("account/", views.account, name="account"),
]
