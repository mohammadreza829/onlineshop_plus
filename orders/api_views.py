from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from drf_spectacular.utils import extend_schema

from .models import Order
from shop.models import Product
from addresses.models import Address
from cart.cart import Cart
from .services import create_order_from_cart, OrderCreationError
from .serializers import (
    CartItemAddSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer
)


class CartAPIView(APIView):
    """
    مدیریت سبد خرید (دریافت لیست، افزودن محصول، حذف محصول)
    """

    def get(self, request):
        """مشاهده محتویات سبد خرید جاری"""
        cart = Cart(request)
        items = []
        for item in cart:
            items.append({
                'product_id': item['product'].id,
                'title': item['product'].title,
                'price': str(item['price']),
                'quantity': item['quantity'],
                'total_price': str(item['total_price']),
            })

        return Response({
            'items': items,
            'total_items_count': len(cart),
            'total_price': cart.get_total_price(),
            'post_price': cart.get_post_price(),
            'final_price': cart.get_final_price(),
        })

    @extend_schema(request=CartItemAddSerializer)
    def post(self, request):
        """افزودن محصول به سبد خرید"""
        serializer = CartItemAddSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']

            product = Product.objects.get(id=product_id)
            cart = Cart(request)
            cart.add(product=product, quantity=quantity,
                     override_quantity=False)

            return Response({"detail": f"محصول '{product.title}' به سبد خرید اضافه شد."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, product_id=None):
        """حذف یک محصول مشخص یا پاک‌سازی کل سبد خرید"""
        cart = Cart(request)
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                cart.remove(product)
                return Response({"detail": "محصول از سبد خرید حذف شد."}, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                return Response({"detail": "محصول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        else:
            cart.clear()
            return Response({"detail": "سبد خرید کاملاً پاک‌سازی شد."}, status=status.HTTP_200_OK)


class OrderListAPIView(ListAPIView):
    """
    مشاهده لیست سفارشات کاربر جاری با امکان فیلتر بر اساس status
    مثال: /api/v1/orders/?status=paid
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Order.objects.filter(
            user=self.request.user).prefetch_related('items')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class OrderDetailAPIView(RetrieveAPIView):
    """مشاهده جزئیات یک سفارش مشخص"""
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class OrderCreateAPIView(APIView):
    """
    ثبت سفارش جدید بر اساس سبد خرید فعلی و آدرس انتخاب‌شده
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=OrderCreateSerializer, responses={210: OrderDetailSerializer})
    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            cart = Cart(request)
            if cart.is_empty:
                return Response({"detail": "سبد خرید شما خالی است."}, status=status.HTTP_400_BAD_REQUEST)

            address_id = serializer.validated_data['address_id']
            selected_address = Address.objects.get(
                id=address_id, user=request.user)

            cleaned_data = {
                'first_name': selected_address.receiver_name.split()[0] if selected_address.receiver_name else request.user.first_name,
                'last_name': ' '.join(selected_address.receiver_name.split()[1:]) if ' ' in selected_address.receiver_name else request.user.last_name,
                'phone': selected_address.receiver_phone,
                'address': f"{selected_address.get_province_display()} - {selected_address.city} - {selected_address.full_address}",
                'postal_code': selected_address.postal_code,
            }

            try:
                order = create_order_from_cart(
                    cart, cleaned_data, request.user)
                order.address_obj = selected_address
                order.save(update_fields=['address_obj'])

                # بازگرداندن پاسخ سفارش همراه با خروجی سریالایزر
                response_serializer = OrderDetailSerializer(order)
                return Response({
                    "message": "سفارش با موفقیت ساخته شد.",
                    "payment_url": request.build_absolute_uri(f"/payment/process/{order.id}/"),
                    "order": response_serializer.data
                }, status=status.HTTP_201_CREATED)

            except OrderCreationError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
