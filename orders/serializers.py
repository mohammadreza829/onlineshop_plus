from rest_framework import serializers

from addresses.models import Address
from shop.models import Product

from .models import Order, OrderItem


class CartItemAddSerializer(serializers.Serializer):
    """سریالایزر افزودن محصول به سبد خرید"""

    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("محصول مورد نظر یافت نشد یا غیرفعال است.")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    """نمایش آیتم‌های درون یک سفارش (نام و قیمت از snapshot خود آیتم خوانده می‌شود)"""

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "product_sku", "price", "quantity", "total_price"]
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    """نمایش کامل جزئیات سفارش ثبت‌شده"""

    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "first_name",
            "last_name",
            "phone",
            "address",
            "postal_code",
            "post_price",
            "total_price",
            "status",
            "status_display",
            "is_paid",
            "ref_id",
            "items",
            "created",
        ]
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    """ورودی ثبت سفارش جدید توسط کاربر"""

    address_id = serializers.IntegerField()

    def validate_address_id(self, value):
        user = self.context["request"].user
        if not Address.objects.filter(id=value, user=user).exists():
            raise serializers.ValidationError("آدرس انتخاب‌شده معتبر نیست یا متعلق به شما نمی‌باشد.")
        return value
