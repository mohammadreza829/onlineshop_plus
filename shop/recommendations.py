"""Anonymous category/popularity recommendations; cache IDs, never price or inventory."""

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Case, F, IntegerField, OuterRef, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from orders.models import Order, OrderItem

from .selectors import catalog_products

logger = logging.getLogger(__name__)
GENERATION_KEY = "catalog:recommendations:generation"
MAX_RECOMMENDATIONS = 20
POOL_SIZE = 60


def invalidate_recommendations():
    try:
        cache.set(GENERATION_KEY, uuid.uuid4().hex, timeout=None)
    except Exception:
        logger.warning("recommendation_cache_invalidation_unavailable")


def catalog_changed(sender, **kwargs):
    transaction.on_commit(invalidate_recommendations)


def _key(product):
    generation = cache.get(GENERATION_KEY)
    if not generation:
        cache.add(GENERATION_KEY, uuid.uuid4().hex, timeout=None)
        generation = cache.get(GENERATION_KEY)
    return f"catalog:recommendations:v1:{generation}:{product.pk}"


def _candidates(product):
    sales = (
        OrderItem.objects.filter(
            product_id=OuterRef("pk"),
            order__is_paid=True,
            order__status__in=[
                Order.STATUS_PAID,
                Order.STATUS_PREPARING,
                Order.STATUS_SENT,
                Order.STATUS_DELIVERED,
            ],
            order__paid_at__gte=timezone.now() - timedelta(days=90),
        )
        .values("product_id")
        .annotate(units=Sum("quantity"))
        .values("units")
    )
    affinity = (
        Case(
            When(category_id=product.category_id, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
        if product.category_id
        else Value(0)
    )
    return list(
        catalog_products(stock="available")
        .exclude(pk=product.pk)
        .annotate(
            recommendation_affinity=affinity,
            popular_units=Coalesce(Subquery(sales), Value(0)),
        )
        .order_by(
            "-recommendation_affinity",
            "-popular_units",
            F("rating_average").desc(nulls_last=True),
            "-created",
            "pk",
        )
        .values_list("pk", flat=True)[:POOL_SIZE]
    )


def _hydrate(product, ids, limit):
    if not ids:
        return []
    order = Case(*[When(pk=pk, then=Value(n)) for n, pk in enumerate(ids)], output_field=IntegerField())
    return list(
        catalog_products(stock="available").filter(pk__in=ids).exclude(pk=product.pk).order_by(order)[:limit]
    )


def recommended_products(product, limit=8):
    if not 1 <= limit <= MAX_RECOMMENDATIONS:
        raise ValueError("Recommendation limit out of range")
    ids = None
    key = None
    # Do not publish uncommitted catalog/orders into shared cache.
    if not connection.in_atomic_block and settings.RECOMMENDATIONS_CACHE_SECONDS > 0:
        try:
            key = _key(product)
            ids = cache.get(key)
            if (
                not isinstance(ids, list)
                or len(ids) > POOL_SIZE
                or any(type(pk) is not int or pk <= 0 for pk in ids)
            ):
                ids = None
        except Exception:
            logger.warning("recommendation_cache_read_unavailable")
    if ids is None:
        ids = _candidates(product)
        if key:
            try:
                cache.set(key, ids, timeout=settings.RECOMMENDATIONS_CACHE_SECONDS)
            except Exception:
                logger.warning("recommendation_cache_write_unavailable")
    result = _hydrate(product, ids, limit)
    if len(result) < min(limit, len(ids)):
        # Refresh if cached candidates have since been hidden/sold out.
        ids = _candidates(product)
        result = _hydrate(product, ids, limit)
        if key:
            try:
                cache.set(key, ids, timeout=settings.RECOMMENDATIONS_CACHE_SECONDS)
            except Exception:
                logger.warning("recommendation_cache_write_unavailable")
    return result
