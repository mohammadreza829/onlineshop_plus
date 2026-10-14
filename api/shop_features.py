from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.models import Favorite, Product, Review
from shop.recommendations import recommended_products
from shop.selectors import catalog_products
from shop.services import save_review

from .serializers import MessageSerializer, ProductSerializer


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        # Never expose customer phone, name, user id or shipping data publicly.
        fields = ["id", "rating", "text", "created", "updated"]
        read_only_fields = fields


class MyReviewSerializer(ReviewSerializer):
    class Meta(ReviewSerializer.Meta):
        fields = [*ReviewSerializer.Meta.fields, "status"]
        read_only_fields = fields


class ReviewInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(min_length=1, max_length=2000)


class ReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        product = get_object_or_404(Product, slug=self.kwargs["slug"], is_active=True)
        return Review.objects.filter(product=product, status=Review.APPROVED)


class MyReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "shop_write"

    def product(self, slug):
        return get_object_or_404(Product, slug=slug, is_active=True)

    @extend_schema(responses=MyReviewSerializer, tags=["Reviews"])
    def get(self, request, slug):
        review = get_object_or_404(Review, user=request.user, product=self.product(slug))
        return Response(MyReviewSerializer(review).data)

    @extend_schema(request=ReviewInputSerializer, responses=MyReviewSerializer, tags=["Reviews"])
    def put(self, request, slug):
        data = ReviewInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        review = save_review(user=request.user, product=self.product(slug), **data.validated_data)
        return Response(MyReviewSerializer(review).data)

    @extend_schema(responses={204: None}, tags=["Reviews"])
    def delete(self, request, slug):
        Review.objects.filter(user=request.user, product=self.product(slug)).delete()
        return Response(status=204)


class FavoriteListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return (
            catalog_products().filter(favorites__user=self.request.user).order_by("-favorites__created", "pk")
        )


class FavoriteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "shop_write"

    @extend_schema(request=None, responses=MessageSerializer, tags=["Favorites"])
    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk, is_active=True)
        Favorite.objects.get_or_create(user=request.user, product=product)
        return Response({"detail": "به علاقه‌مندی‌ها اضافه شد."})

    @extend_schema(responses={204: None}, tags=["Favorites"])
    def delete(self, request, pk):
        Favorite.objects.filter(user=request.user, product_id=pk).delete()
        return Response(status=204)


class RecommendationFilterSerializer(serializers.Serializer):
    limit = serializers.IntegerField(default=8, min_value=1, max_value=20)


class RecommendationView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer

    @extend_schema(
        parameters=[RecommendationFilterSerializer],
        responses=ProductSerializer(many=True),
        tags=["Recommendations"],
    )
    def get(self, request, slug):
        params = RecommendationFilterSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        product = get_object_or_404(Product, slug=slug, is_active=True)
        products = recommended_products(product, limit=params.validated_data["limit"])
        return Response(self.get_serializer(products, many=True).data)
