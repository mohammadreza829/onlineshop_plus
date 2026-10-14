"""Framework-neutral bootstrap. Never exposes secrets or selects a frontend stack."""

from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from addresses.models import Address
from cart.services import MAX_QUANTITY_PER_REQUEST

from .pagination import BoundedPagination


class CSRFSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(responses=CSRFSerializer, tags=["Client bootstrap"])
    def get(self, request):
        # Use the original Django request so CsrfViewMiddleware sets the cookie.
        return Response({"csrf_token": get_token(request._request)})


class ProvinceOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class ClientOptionsSerializer(serializers.Serializer):
    currency = serializers.CharField()
    time_zone = serializers.CharField()
    cart_quantity_max = serializers.IntegerField()
    cart_lines_max = serializers.IntegerField()
    pagination_default = serializers.IntegerField()
    pagination_max = serializers.IntegerField()
    provinces = ProvinceOptionSerializer(many=True)


class ClientOptionsView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(responses=ClientOptionsSerializer, tags=["Client bootstrap"])
    def get(self, request):
        return Response(
            {
                "currency": "TOMAN",
                "time_zone": settings.TIME_ZONE,
                "cart_quantity_max": MAX_QUANTITY_PER_REQUEST,
                "cart_lines_max": settings.CART_MAX_LINES,
                "pagination_default": BoundedPagination.default_limit,
                "pagination_max": BoundedPagination.max_limit,
                "provinces": [{"value": value, "label": label} for value, label in Address.PROVINCE_CHOICES],
            }
        )
