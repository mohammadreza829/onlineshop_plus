from django.urls import path

from orders.api_views import (
    CartAPIView,
    CartItemDeleteAPIView,
    OrderCreateAPIView,
    OrderDetailAPIView,
    OrderListAPIView,
)

from . import auth_views, views

app_name = "api_v1"
urlpatterns = [
    path("auth/otp/request/", auth_views.OTPRequestView.as_view(), name="otp_request"),
    path("auth/otp/verify/", auth_views.OTPVerifyView.as_view(), name="otp_verify"),
    path("auth/token/refresh/", auth_views.RefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("me/", views.ProfileView.as_view(), name="profile"),
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/<slug:slug>/", views.CategoryDetailView.as_view(), name="category_detail"),
    path("addresses/", views.AddressListView.as_view(), name="address_list"),
    path("addresses/<int:pk>/", views.AddressDetailView.as_view(), name="address_detail"),
    path("cart/", CartAPIView.as_view(), name="cart"),
    path("cart/items/<int:product_id>/", CartItemDeleteAPIView.as_view(), name="cart_item"),
    path("orders/", OrderListAPIView.as_view(), name="order_list"),
    path("orders/create/", OrderCreateAPIView.as_view(), name="order_create"),
    path("orders/<int:id>/", OrderDetailAPIView.as_view(), name="order_detail"),
    path("orders/<int:pk>/cancel/", views.OrderCancelView.as_view(), name="order_cancel"),
    path("orders/<int:pk>/payment/", views.OrderPaymentView.as_view(), name="order_payment"),
]
