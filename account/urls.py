from django.urls import path

from . import views

app_name = "account"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/verify/", views.verify_code_view, name="verify_code"),
    path("profile/", views.profile_view, name="profile"),
    path("logout/", views.logout_view, name="logout"),
]
