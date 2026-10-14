from rest_framework import serializers

from addresses.selectors import addresses_for_user
from cart.services import MAX_QUANTITY_PER_REQUEST
from shop.models import Product

from .models import Order, OrderItem


class CartItemAddSerializer(serializers.Serializer):
    """سریالایزر افزودن محصول به سبد خرید"""

    variant_id = serializers.IntegerField(required=False, min_value=1)
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(default=1, min_value=1, max_value=MAX_QUANTITY_PER_REQUEST)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("محصول مورد نظر یافت نشد یا غیرفعال است.")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    """نمایش آیتم‌های درون یک سفارش (نام و قیمت از snapshot خود آیتم خوانده می‌شود)"""

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "variant",
            "variant_sku",
            "variant_color",
            "variant_size",
            "price",
            "quantity",
            "total_price",
        ]
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    """نمایش کامل جزئیات سفارش ثبت‌شده"""

    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    is_payable = serializers.BooleanField(read_only=True)

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
            "coupon_code",
            "coupon_discount",
            "status",
            "status_display",
            "is_paid",
            "ref_id",
            "reserved_until",
            "is_payable",
            "items",
            "created",
        ]
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    """ورودی ثبت سفارش جدید توسط کاربر"""

    coupon_code = serializers.RegexField(r"^[a-zA-Z0-9_-]{1,40}$", required=False)
    address_id = serializers.IntegerField()

    def validate_address_id(self, value):
        user = self.context["request"].user
        if not addresses_for_user(user).filter(id=value).exists():
            raise serializers.ValidationError("آدرس انتخاب‌شده معتبر نیست یا متعلق به شما نمی‌باشد.")
        return value
