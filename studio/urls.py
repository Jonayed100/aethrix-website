from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("", views.home, name="home"),
    path("book/", views.book, name="book"),
    path("book/thanks/<str:reference>/", views.booking_thanks, name="booking_thanks"),
]
