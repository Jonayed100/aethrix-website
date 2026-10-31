from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path("verify/resend/", views.resend_verification, name="verify_resend"),
    path("verify/<str:token>/", views.verify_email, name="verify"),
    path("password/forgot/", views.ForgotPasswordView.as_view(), name="password_forgot"),
    path("password/forgot/sent/", views.ForgotPasswordSentView.as_view(), name="password_forgot_sent"),
    path("password/set/<uidb64>/<token>/", views.SetPasswordView.as_view(), name="password_set"),
]
