from django.urls import path

from .views import (
    CsrfTokenView,
    CurrentUserView,
    LoginView,
    LogoutView,
    StudentRegistrationView,
)


urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("register/", StudentRegistrationView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", CurrentUserView.as_view(), name="auth-me"),
]
