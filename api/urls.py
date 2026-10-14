from django.urls import path

from orders.api_views import (
    CartAPIView,
    CartItemAPIView,
    OrderCreateAPIView,
    OrderDetailAPIView,
    OrderListAPIView,
)

from . import auth_views, client_contract, operations, shop_features, views

app_name = "api_v1"
urlpatterns = [
    path("csrf/", client_contract.CSRFView.as_view(), name="csrf"),
    path("client-options/", client_contract.ClientOptionsView.as_view(), name="client_options"),
    path("notifications/", operations.NotificationListView.as_view(), name="notifications"),
    path("notifications/<int:pk>/read/", operations.NotificationReadView.as_view(), name="notification_read"),
    path("orders/<int:pk>/tracking/", operations.TrackingView.as_view(), name="tracking"),
    path("staff/orders/<int:pk>/", operations.StaffOrderView.as_view(), name="staff_order"),
    path("staff/sales/", operations.SalesDashboardView.as_view(), name="sales_dashboard"),
    path("auth/otp/request/", auth_views.OTPRequestView.as_view(), name="otp_request"),
    path("auth/otp/verify/", auth_views.OTPVerifyView.as_view(), name="otp_verify"),
    path("auth/token/refresh/", auth_views.RefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("me/", views.ProfileView.as_view(), name="profile"),
    path(
        "products/<slug:slug>/recommendations/",
        shop_features.RecommendationView.as_view(),
        name="recommendations",
    ),
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("products/<slug:slug>/reviews/", shop_features.ReviewListView.as_view(), name="reviews"),
    path("products/<slug:slug>/reviews/mine/", shop_features.MyReviewView.as_view(), name="my_review"),
    path("products/<int:pk>/favorite/", shop_features.FavoriteView.as_view(), name="favorite"),
    path("favorites/", shop_features.FavoriteListView.as_view(), name="favorites"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/<slug:slug>/", views.CategoryDetailView.as_view(), name="category_detail"),
    path("addresses/", views.AddressListView.as_view(), name="address_list"),
    path("addresses/<int:pk>/", views.AddressDetailView.as_view(), name="address_detail"),
    path("cart/", CartAPIView.as_view(), name="cart"),
    path("cart/items/<int:product_id>/", CartItemAPIView.as_view(), name="cart_item"),
    path("orders/", OrderListAPIView.as_view(), name="order_list"),
    path("orders/create/", OrderCreateAPIView.as_view(), name="order_create"),
    path("orders/<int:id>/", OrderDetailAPIView.as_view(), name="order_detail"),
    path("orders/<int:pk>/cancel/", views.OrderCancelView.as_view(), name="order_cancel"),
    path("orders/<int:pk>/payment/", views.OrderPaymentView.as_view(), name="order_payment"),
]
