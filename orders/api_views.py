from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from addresses.selectors import addresses_for_user
from api.serializers import (
    CartSerializer,
    CheckoutResponseSerializer,
    MessageSerializer,
    OrderFilterSerializer,
)
from cart.cart import Cart
from shop.models import Product, ProductVariant

from .selectors import orders_for_user
from .serializers import CartItemAddSerializer, OrderCreateSerializer, OrderDetailSerializer
from .services import OrderCreationError, create_order_from_cart


class CartAPIView(APIView):
    """
    مدیریت سبد خرید (دریافت لیست، افزودن محصول، حذف محصول).
    سبد خرید در session نگه‌داری می‌شود، پس برای مهمان هم در دسترس است.
    """

    permission_classes = [permissions.AllowAny]
    throttle_scope = "cart"

    @extend_schema(responses=CartSerializer, tags=["Cart"])
    def get(self, request):
        """مشاهده محتویات سبد خرید جاری"""
        cart = Cart(request)
        cart.clean()
        items = [
            {
                "product_id": item["product"].id,
                "variant_id": item["variant"].id if item.get("variant") else None,
                "name": item["product"].name,
                "price": str(item["price"]),
                "quantity": item["quantity"],
                "total_price": str(item["total_price"]),
            }
            for item in cart
        ]
        return Response({"items": items, **cart.summary()})

    @extend_schema(request=CartItemAddSerializer, responses=MessageSerializer, tags=["Cart"])
    def post(self, request):
        """افزودن محصول به سبد خرید"""
        serializer = CartItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = get_object_or_404(Product, id=serializer.validated_data["product_id"], is_active=True)
        variant_id = serializer.validated_data.get("variant_id")
        variant = get_object_or_404(ProductVariant, pk=variant_id, product=product) if variant_id else None
        result = Cart(request).add(
            product=product, quantity=serializer.validated_data["quantity"], variant=variant
        )

        response_status = status.HTTP_200_OK if result.success else status.HTTP_400_BAD_REQUEST
        return Response({"detail": result.message}, status=response_status)

    @extend_schema(responses=MessageSerializer, tags=["Cart"])
    def delete(self, request, product_id=None):
        """حذف یک محصول مشخص یا پاک‌سازی کل سبد خرید"""
        cart = Cart(request)
        if product_id is None:
            cart.clear()
            return Response({"detail": "سبد خرید کاملاً پاک‌سازی شد."}, status=status.HTTP_200_OK)

        product = get_object_or_404(Product, id=product_id)
        params = CartItemAddSerializer(data={"product_id": product_id, **request.query_params.dict()})
        params.is_valid(raise_exception=True)
        variant_id = params.validated_data.get("variant_id")
        variant = get_object_or_404(ProductVariant, pk=variant_id, product=product) if variant_id else None
        result = cart.remove(product, variant=variant)
        response_status = status.HTTP_200_OK if result.success else status.HTTP_404_NOT_FOUND
        return Response({"detail": result.message}, status=response_status)


@extend_schema_view(get=extend_schema(parameters=[OrderFilterSerializer], tags=["Orders"]))
class OrderListAPIView(ListAPIView):
    """
    مشاهده لیست سفارش‌های کاربر جاری با امکان فیلتر بر اساس status
    مثال: /orders/api/v1/orders/?status=paid
    """

    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        params = OrderFilterSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return orders_for_user(self.request.user, status=params.validated_data.get("status"))


@extend_schema_view(get=extend_schema(tags=["Orders"]))
class OrderDetailAPIView(RetrieveAPIView):
    """مشاهده جزئیات یک سفارش مشخص"""

    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return orders_for_user(self.request.user)


class OrderCreateAPIView(APIView):
    """ثبت سفارش جدید بر اساس سبد خرید فعلی و آدرس انتخاب‌شده"""

    permission_classes = [permissions.IsAuthenticated]

    throttle_scope = "checkout"

    @extend_schema(
        request=OrderCreateSerializer, responses={201: CheckoutResponseSerializer}, tags=["Orders"]
    )
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        cart = Cart(request)
        if cart.is_empty:
            return Response({"detail": "سبد خرید شما خالی است."}, status=status.HTTP_400_BAD_REQUEST)

        selected_address = get_object_or_404(
            addresses_for_user(request.user), id=serializer.validated_data["address_id"]
        )

        try:
            order = create_order_from_cart(
                cart,
                selected_address,
                request.user,
                coupon_code=serializer.validated_data.get("coupon_code", ""),
            )
        except OrderCreationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "سفارش با موفقیت ساخته شد.",
                # POST to this URL (session auth + CSRF) to be redirected to the gateway.
                "payment_url": request.build_absolute_uri(reverse("payment:process", args=[order.id])),
                "payment_api_url": request.build_absolute_uri(
                    reverse("api_v1:order_payment", args=[order.id])
                ),
                "reserved_until": order.reserved_until,
                "order": OrderDetailSerializer(order).data,
            },
            status=status.HTTP_201_CREATED,
        )


class CartItemDeleteAPIView(CartAPIView):
    http_method_names = ["delete", "options"]


@extend_schema(exclude=True)
class LegacyCartAPIView(CartAPIView):
    pass


@extend_schema(exclude=True)
class LegacyCartItemDeleteAPIView(CartItemDeleteAPIView):
    pass


@extend_schema(exclude=True)
class LegacyOrderListAPIView(OrderListAPIView):
    pass


@extend_schema(exclude=True)
class LegacyOrderDetailAPIView(OrderDetailAPIView):
    pass


@extend_schema(exclude=True)
class LegacyOrderCreateAPIView(OrderCreateAPIView):
    pass
