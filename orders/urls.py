from django.urls import path

from . import api_views, views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="order_list"),
    path("create/", views.order_create, name="order_create"),
    path("<int:order_id>/", views.order_detail, name="order_detail"),
    path("<int:order_id>/cancel/", views.order_cancel, name="order_cancel"),
    # API
    path("api/v1/cart/", api_views.CartAPIView.as_view(), name="api_cart"),
    path("api/v1/cart/delete/<int:product_id>/", api_views.CartAPIView.as_view(), name="api_cart_delete_item"),
    path("api/v1/orders/", api_views.OrderListAPIView.as_view(), name="api_order_list"),
    path("api/v1/orders/<int:id>/", api_views.OrderDetailAPIView.as_view(), name="api_order_detail"),
    path("api/v1/orders/create/", api_views.OrderCreateAPIView.as_view(), name="api_order_create"),
]
