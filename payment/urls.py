from django.urls import path

from . import demo_views, views

app_name = "payment"

urlpatterns = [
    path("demo/<str:authority>/", demo_views.demo_payment, name="demo"),
    path("process/<int:order_id>/", views.payment_process, name="process"),
    path("verify/", views.payment_verify, name="verify"),
]
