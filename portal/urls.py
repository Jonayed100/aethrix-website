from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("orders/<str:reference>/", views.order_detail, name="order"),
    path("account/", views.account, name="account"),
]
