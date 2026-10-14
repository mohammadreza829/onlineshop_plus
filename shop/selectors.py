"""Read-side catalog queries shared by HTML and API. Prices are whole Toman."""

from django.db.models import Q

from .models import Category, Product


def catalog_products(
    *, search="", category=None, stock=None, ordering="-created", min_price=None, max_price=None
):
    qs = Product.objects.filter(is_active=True).select_related("category")
    if search:
        qs = qs.filter(
            Q(name__icontains=search) | Q(description__icontains=search) | Q(sku__icontains=search)
        )
    if category:
        qs = qs.filter(category__slug=category)
    if stock == "available":
        qs = qs.filter(inventory__gt=0)
    elif stock == "out":
        qs = qs.filter(inventory=0)
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    if ordering not in {"price", "-price", "created", "-created", "name", "-name"}:
        ordering = "-created"
    return qs.order_by(ordering, "pk")


def catalog_detail():
    return catalog_products().prefetch_related("features", "images")


def categories(*, search="", parent=None, roots_only=False):
    qs = Category.objects.select_related("parent")
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(slug__icontains=search))
    if parent is not None:
        qs = qs.filter(parent_id=parent)
    if roots_only:
        qs = qs.filter(parent__isnull=True)
    return qs.order_by("name", "pk")
