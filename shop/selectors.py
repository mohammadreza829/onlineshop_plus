"""Read-side catalog queries shared by HTML and API. Prices are whole Toman."""

from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from .models import Category, Product, ProductVariant, Review
from .search import normalize_search, search_products


def catalog_products(
    *, search="", category=None, stock=None, ordering="-created", min_price=None, max_price=None
):
    ratings = (
        Review.objects.filter(product_id=OuterRef("pk"), status=Review.APPROVED)
        .values("product_id")
        .annotate(average=Avg("rating"), total=Count("pk"))
    )
    variants = ProductVariant.objects.filter(product_id=OuterRef("pk"))
    totals = variants.filter(is_active=True).values("product_id").annotate(total=Sum("inventory"))
    qs = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .annotate(
            rating_average=Subquery(ratings.values("average")),
            rating_count=Coalesce(Subquery(ratings.values("total")), Value(0)),
            has_variants=Exists(variants),
            stock_available=Case(
                When(has_variants=True, then=Coalesce(Subquery(totals.values("total")), Value(0))),
                default=F("inventory"),
                output_field=IntegerField(),
            ),
        )
    )
    search = normalize_search(search)
    if search:
        qs = search_products(qs, search)
    if category:
        qs = qs.filter(category__slug=category)
    if stock == "available":
        qs = qs.filter(stock_available__gt=0)
    elif stock == "out":
        qs = qs.filter(stock_available=0)
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    if ordering == "relevance":
        return (
            qs.order_by("-search_rank", "pk")
            if search and "search_rank" in qs.query.annotations
            else qs.order_by("-created", "pk")
        )
    if ordering not in {"price", "-price", "created", "-created", "name", "-name"}:
        ordering = "-created"
    return qs.order_by(ordering, "pk")


def catalog_detail():
    return catalog_products().prefetch_related("features", "images", "variants")


def categories(*, search="", parent=None, roots_only=False):
    qs = Category.objects.select_related("parent")
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(slug__icontains=search))
    if parent is not None:
        qs = qs.filter(parent_id=parent)
    if roots_only:
        qs = qs.filter(parent__isnull=True)
    return qs.order_by("name", "pk")
