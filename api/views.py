from addresses.services import save_address
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from shop.selectors import catalog_detail, catalog_products, categories

from addresses.selectors import addresses_for_user
from orders.selectors import orders_for_user
from orders.serializers import OrderDetailSerializer
from orders.services import OrderActionError, cancel_order_by_customer
from payment.services import PaymentError, callback_url_for_request, start_payment

from .permissions import IsOwner
from .serializers import (
    AddressSerializer,
    CatalogFilterSerializer,
    CategoryFilterSerializer,
    CategorySerializer,
    CustomerSerializer,
    PaymentLinkSerializer,
    ProductDetailSerializer,
    ProductSerializer,
)


@extend_schema_view(get=extend_schema(parameters=[CatalogFilterSerializer], tags=["Catalog"]))
class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        params = CatalogFilterSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return catalog_products(**params.validated_data)


@extend_schema_view(get=extend_schema(tags=["Catalog"]))
class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    queryset = catalog_detail()
    lookup_field = "slug"


@extend_schema_view(get=extend_schema(parameters=[CategoryFilterSerializer], tags=["Catalog"]))
class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        params = CategoryFilterSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return categories(**params.validated_data)


@extend_schema_view(get=extend_schema(tags=["Catalog"]))
class CategoryDetailView(generics.RetrieveAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    queryset = categories()
    lookup_field = "slug"


@extend_schema_view(get=extend_schema(tags=["Account"]), patch=extend_schema(tags=["Account"]))
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class AddressMixin:
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return addresses_for_user(self.request.user)

    def perform_create(self, serializer):
        serializer.instance = save_address(user=self.request.user, data=serializer.validated_data)

    def perform_update(self, serializer):
        serializer.instance = save_address(
            user=self.request.user, address=serializer.instance, data=serializer.validated_data
        )


@extend_schema_view(get=extend_schema(tags=["Addresses"]), post=extend_schema(tags=["Addresses"]))
class AddressListView(AddressMixin, generics.ListCreateAPIView):
    pass


@extend_schema_view(
    get=extend_schema(tags=["Addresses"]),
    patch=extend_schema(tags=["Addresses"]),
    delete=extend_schema(tags=["Addresses"]),
)
class AddressDetailView(AddressMixin, generics.RetrieveUpdateDestroyAPIView):
    http_method_names = ["get", "patch", "delete", "head", "options"]


class OrderCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    throttle_scope = "checkout"

    @extend_schema(request=None, responses={200: OrderDetailSerializer}, tags=["Orders"])
    def post(self, request, pk):
        order = get_object_or_404(orders_for_user(request.user), pk=pk)
        try:
            order = cancel_order_by_customer(order, request.user)
        except OrderActionError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(OrderDetailSerializer(order).data)


class OrderPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    throttle_scope = "checkout"

    @extend_schema(request=None, responses={200: PaymentLinkSerializer}, tags=["Payments"])
    def post(self, request, pk):
        order = get_object_or_404(orders_for_user(request.user), pk=pk)
        try:
            url = start_payment(order, request.user, callback_url_for_request(request))
        except PaymentError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({"payment_url": url}, status=status.HTTP_200_OK)
