from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from addresses.models import Address
from cart.cart import Cart
from shop.models import Product

from .models import Order
from .serializers import CartItemAddSerializer, OrderCreateSerializer, OrderDetailSerializer
from .services import OrderCreationError, create_order_from_cart


class CartAPIView(APIView):
    """
    مدیریت سبد خرید (دریافت لیست، افزودن محصول، حذف محصول).
    سبد خرید در session نگه‌داری می‌شود، پس برای مهمان هم در دسترس است.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """مشاهده محتویات سبد خرید جاری"""
        cart = Cart(request)
        cart.clean()
        items = [
            {
                "product_id": item["product"].id,
                "name": item["product"].name,
                "price": str(item["price"]),
                "quantity": item["quantity"],
                "total_price": str(item["total_price"]),
            }
            for item in cart
        ]
        return Response({"items": items, **cart.summary()})

    @extend_schema(request=CartItemAddSerializer)
    def post(self, request):
        """افزودن محصول به سبد خرید"""
        serializer = CartItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = get_object_or_404(Product, id=serializer.validated_data["product_id"], is_active=True)
        result = Cart(request).add(product=product, quantity=serializer.validated_data["quantity"])

        response_status = status.HTTP_200_OK if result.success else status.HTTP_400_BAD_REQUEST
        return Response({"detail": result.message}, status=response_status)

    def delete(self, request, product_id=None):
        """حذف یک محصول مشخص یا پاک‌سازی کل سبد خرید"""
        cart = Cart(request)
        if product_id is None:
            cart.clear()
            return Response({"detail": "سبد خرید کاملاً پاک‌سازی شد."}, status=status.HTTP_200_OK)

        product = get_object_or_404(Product, id=product_id)
        result = cart.remove(product)
        response_status = status.HTTP_200_OK if result.success else status.HTTP_404_NOT_FOUND
        return Response({"detail": result.message}, status=response_status)


class OrderListAPIView(ListAPIView):
    """
    مشاهده لیست سفارش‌های کاربر جاری با امکان فیلتر بر اساس status
    مثال: /orders/api/v1/orders/?status=paid
    """

    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user).prefetch_related("items")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class OrderDetailAPIView(RetrieveAPIView):
    """مشاهده جزئیات یک سفارش مشخص"""

    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class OrderCreateAPIView(APIView):
    """ثبت سفارش جدید بر اساس سبد خرید فعلی و آدرس انتخاب‌شده"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=OrderCreateSerializer, responses={201: OrderDetailSerializer})
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        cart = Cart(request)
        if cart.is_empty:
            return Response({"detail": "سبد خرید شما خالی است."}, status=status.HTTP_400_BAD_REQUEST)

        selected_address = get_object_or_404(
            Address, id=serializer.validated_data["address_id"], user=request.user
        )

        try:
            order = create_order_from_cart(cart, selected_address, request.user)
        except OrderCreationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "سفارش با موفقیت ساخته شد.",
                # POST to this URL (session auth + CSRF) to be redirected to the gateway.
                "payment_url": request.build_absolute_uri(reverse("payment:process", args=[order.id])),
                "reserved_until": order.reserved_until,
                "order": OrderDetailSerializer(order).data,
            },
            status=status.HTTP_201_CREATED,
        )
