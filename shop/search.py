"""Persian-friendly normalization; indexed websearch on PostgreSQL, AND fallback on SQLite."""

import re

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db import connection
from django.db.models import F, Func, Q, TextField

_TRANSLATION = str.maketrans("يك٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹\u200c\u200d\u0640", "یک01234567890123456789   ")


def normalize_search(value):
    # Explicit normalization is also implemented by the PostgreSQL trigger migration.
    value = str(value or "").translate(_TRANSLATION).lower()
    value = re.sub("[\u064b-\u065f\u0670]", "", value)
    return " ".join(value.split())


def register_sqlite_search(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        connection.connection.create_function(
            "shop_normalize_search", 1, normalize_search, deterministic=True
        )


def search_products(qs, text):
    text = normalize_search(text)
    if not text:
        return qs
    if connection.vendor == "postgresql":
        query = SearchQuery(text, search_type="websearch", config="simple")
        return qs.filter(search_document=query).annotate(search_rank=SearchRank(F("search_document"), query))
    # SQLite development fallback: normalized substrings, all terms required.
    fields = ["name", "description", "sku"]
    qs = qs.annotate(
        **{
            f"search_{f}": Func(F(f), function="shop_normalize_search", output_field=TextField())
            for f in fields
        }
    )
    for term in text.split():
        qs = qs.filter(
            Q(search_name__icontains=term)
            | Q(search_description__icontains=term)
            | Q(search_sku__icontains=term)
        )
    return qs
