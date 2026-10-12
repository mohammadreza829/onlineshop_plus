from rest_framework import serializers
from shop.models import Product


class ProductSerializaer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['name', 'description','price']