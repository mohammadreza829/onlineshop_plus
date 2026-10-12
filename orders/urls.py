from django.urls import path

from . import views, api_views

app_name = "orders"

urlpatterns = [

    path(
        "create/",
        views.order_create,
        name="order_create",
    ),

    path(
        "<int:order_id>/",
        views.order_detail,
        name="order_detail",
    ),

    path(
        "",
        views.order_list,
        name="order_list",
    ),
    path('verify-phone/', views.verify_phone, name='verify_phone'),
    path('verify-code/', views.verify_code, name='verify_code'),
    # path(
    #     "payment/<int:order_id>/",
    #     views.payment_request,
    #     name="payment_request"
    # ),
    path('api/v1/cart/', api_views.CartAPIView.as_view(), name='api_cart'),
    path('api/v1/cart/delete/<int:product_id>/',
         api_views.CartAPIView.as_view(), name='api_cart_delete_item'),
    path('api/v1/orders/', api_views.OrderListAPIView.as_view(),
         name='api_order_list'),
    path('api/v1/orders/<int:id>/',
         api_views.OrderDetailAPIView.as_view(), name='api_order_detail'),
    path('api/v1/orders/create/', api_views.OrderCreateAPIView.as_view(),
         name='api_order_create'),



    # path(
    #     "payment/verify/",
    #     views.payment_verify,
    #     name="payment_verify"
    # ),

]
