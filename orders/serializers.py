from rest_framework import serializers
from .models import Order, OrderItem
from addresses.models import Address
from shop.models import Product


class CartItemAddSerializer(serializers.Serializer):
    """ ﺳﺮﯾﺎﻻ ﺰر ﺑﺮایو/ اﻓﺰودن ﺮاﯾﺶ ﻣﺤﺼﻮل در ﺳﺒﺪ ﺧﺮﯾﺪ """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)

    def validate_product_id(self, value):
        if not Product.objects.ﬁlter(id=value, is_active=True).exists():
            raise serializers.ValidationError(
                " ﻣﺤﺼﻮل ﻣﻮرد ﻧﻈﺮ ﯾﺎﻓﺖ ﻧﺸﺪ ﯾﺎ ﻏ ﺮﻓﻌﺎل اﺳﺖ .")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    """ ﻧﻤﺎﯾﺶ ﻫﺎیآﯾﺘﻢ درون ﯾﮏ ﺳﻔﺎرش """
    product_name = serializers.ReadOnlyField(source='product.title')
    price = serializers.ReadOnlyField(source='price')

    class Meta:
        model = OrderItem
        ﬁelds = ['id', 'product', 'product_name', 'price', 'quantity']

class OrderDetailSerializer(serializers.ModelSerializer):
    """نمایش کامل جزئیات سفارش ثبت‌شده"""
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'first_name', 'last_name', 'phone', 
            'address', 'postal_code', 'total_price', 'status', 
            'status_display', 'is_paid', 'ref_id', 'items', 'created'
        ]


class OrderCreateSerializer(serializers.Serializer):
    """ورودی ثبت سفارش جدید توسط کاربر"""
    address_id = serializers.IntegerField()

    def validate_address_id(self, value):
        user = self.context['request'].user
        if not Address.objects.filter(id=value, user=user).exists():
            raise serializers.ValidationError("آدرس انتخاب‌شده معتبر نیست یا متعلق به شما نمی‌باشد.")
        return value
