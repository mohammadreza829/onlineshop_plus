from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from account.models import ShopUser
from account.otp import normalize_phone
from addresses.models import Address
from addresses.validation import normalize_postal_code
from orders.models import Order
from orders.serializers import OrderDetailSerializer
from shop.models import Category, Product, ProductFeatures, ProductImage, ProductVariant


class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)

    def validate_phone(self, value):
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc


class OTPVerifySerializer(PhoneSerializer):
    code = serializers.CharField(min_length=6, max_length=6)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class RefreshInputSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopUser
        fields = ["id", "phone", "first_name", "last_name"]
        read_only_fields = ["id", "phone"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent"]
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    inventory = serializers.IntegerField(source="available_stock", read_only=True)
    category = CategorySerializer(read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "sku", "name", "slug", "price", "off", "final_price", "inventory", "category"]
        read_only_fields = fields


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFeatures
        fields = ["id", "name", "value"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "description", "is_primary", "order"]


class VariantSerializer(serializers.ModelSerializer):
    final_price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)

    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "color", "size", "price", "final_price", "inventory", "is_active"]
        read_only_fields = fields


class ProductDetailSerializer(ProductSerializer):
    variants = VariantSerializer(many=True, read_only=True)
    features = FeatureSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta(ProductSerializer.Meta):
        fields = [*ProductSerializer.Meta.fields, "description", "features", "images", "variants"]
        read_only_fields = fields


class CatalogFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=200)
    category = serializers.SlugField(required=False, max_length=250)
    stock = serializers.ChoiceField(choices=["available", "out"], required=False)
    ordering = serializers.ChoiceField(
        choices=["price", "-price", "created", "-created", "name", "-name"], default="-created"
    )
    min_price = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=0, required=False)
    max_price = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=0, required=False)

    def validate(self, attrs):
        if attrs.get("min_price", 0) > attrs.get("max_price", float("inf")):
            raise serializers.ValidationError("حداقل قیمت نمی‌تواند بیشتر از حداکثر باشد.")
        return attrs


class CategoryFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=200)
    parent = serializers.IntegerField(required=False, min_value=1)
    roots_only = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs.get("parent") and attrs.get("roots_only"):
            raise serializers.ValidationError("فیلتر والد و دسته‌های ریشه را هم‌زمان انتخاب نکنید.")
        return attrs


class OrderFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES, required=False)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "title",
            "receiver_name",
            "receiver_phone",
            "province",
            "city",
            "full_address",
            "postal_code",
            "is_default",
        ]
        read_only_fields = ["id"]

    def validate_receiver_phone(self, value):
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate_postal_code(self, value):
        try:
            return normalize_postal_code(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc


class CheckoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    payment_url = serializers.URLField()
    payment_api_url = serializers.URLField()
    reserved_until = serializers.DateTimeField()
    order = OrderDetailSerializer()


class PaymentLinkSerializer(serializers.Serializer):
    payment_url = serializers.URLField()


class CartItemSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(allow_null=True)
    product_id = serializers.IntegerField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=0)
    quantity = serializers.IntegerField()
    total_price = serializers.DecimalField(max_digits=16, decimal_places=0)


class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=16, decimal_places=0)
    post_price = serializers.DecimalField(max_digits=16, decimal_places=0)
    discount = serializers.DecimalField(max_digits=16, decimal_places=0)
    total_price = serializers.DecimalField(max_digits=16, decimal_places=0)
    item_count = serializers.IntegerField()
    is_empty = serializers.BooleanField()
