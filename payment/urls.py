from django.urls import path

from . import views

app_name = "payment"

urlpatterns = [
    path("process/<int:order_id>/", views.payment_process, name="process"),
    path("verify/", views.payment_verify, name="verify"),
    path("storefront/verify/", views.payment_verify, {"storefront": True}, name="storefront_verify"),
]
