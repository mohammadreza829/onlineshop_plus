from unittest import skipUnless

from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from onlineshop.testing import make_product

from .models import Product
from .search import normalize_search
from .selectors import catalog_products


class SearchTests(TestCase):
    def test_persian_arabic_digits_and_spacing_normalization(self):
        self.assertEqual(normalize_search("  كِيف\u200cدستي ۱۲٣ـ "), "کیف دستی 123")

    def test_normalized_terms_and_field_matching(self):
        product = make_product()
        Product.objects.filter(pk=product.pk).update(name="كِيف\u200cدستي ویژه", description="رنگ آبی ۱۲۳")
        self.assertEqual(list(catalog_products(search="کیف دستی").values_list("pk", flat=True)), [product.pk])
        self.assertEqual(list(catalog_products(search="آبي 123").values_list("pk", flat=True)), [product.pk])
        self.assertFalse(catalog_products(search="کیف ناموجود").exists())
        self.assertEqual(
            list(catalog_products(search=product.sku).values_list("pk", flat=True)), [product.pk]
        )

    def test_api_relevance_and_filters_do_not_expose_inactive(self):
        active = make_product()
        inactive = make_product(is_active=False)
        Product.objects.filter(pk__in=[active.pk, inactive.pk]).update(name="چراغ آزمایشی")
        client = APIClient()
        data = client.get("/api/v1/products/?search=چراغ&ordering=relevance").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], active.pk)
        self.assertEqual(client.get("/api/v1/products/?ordering=relevance").status_code, 200)
        self.assertEqual(client.get("/api/v1/products/?search=" + ("a" * 201)).status_code, 400)

    def test_untrusted_search_cannot_inject_sql(self):
        make_product()
        self.assertEqual(
            APIClient()
            .get("/api/v1/products/", {"search": "' OR 1=1; DROP TABLE shop_product; --"})
            .status_code,
            200,
        )
        self.assertEqual(Product.objects.count(), 1)


@skipUnless(connection.vendor == "postgresql", "requires PostgreSQL full-text index/trigger")
class PostgreSQLSearchTests(TestCase):
    def test_weighted_ranking_and_websearch(self):
        name = make_product()
        description = make_product()
        Product.objects.filter(pk=name.pk).update(name="چراغ")
        Product.objects.filter(pk=description.pk).update(description="چراغ")
        self.assertEqual(
            list(catalog_products(search="چراغ", ordering="relevance").values_list("pk", flat=True)),
            [name.pk, description.pk],
        )
        self.assertEqual(catalog_products(search="چراغ OR ناموجود").count(), 2)
        self.assertEqual(catalog_products(search="چراغ -ناموجود").count(), 2)

    def test_trigger_covers_bulk_create_update_and_raw_sql(self):
        Product.objects.bulk_create(
            [Product(name="کفش اولیه", sku="bulk-search", slug="bulk-search", price=10)]
        )
        product = Product.objects.get(sku="bulk-search")
        self.assertIsNotNone(product.search_document)
        self.assertTrue(catalog_products(search="کفش اولیه").filter(pk=product.pk).exists())
        with connection.cursor() as cursor:
            cursor.execute("UPDATE shop_product SET name=%s WHERE id=%s", ["کتاب تازه", product.pk])
        self.assertFalse(catalog_products(search="کفش اولیه").filter(pk=product.pk).exists())
        self.assertTrue(catalog_products(search="کتاب تازه").filter(pk=product.pk).exists())

    def test_normalizer_matches_postgresql_function_and_gin_exists(self):
        text = "  كِيف\u200cدستي ۱۲٣ـ "
        with connection.cursor() as cursor:
            cursor.execute("SELECT shop_normalize_search(%s)", [text])
            self.assertEqual(cursor.fetchone()[0], normalize_search(text))
            cursor.execute(
                "SELECT indexdef FROM pg_indexes WHERE tablename='shop_product' AND indexname='product_search_gin'"
            )
            self.assertIn("USING gin", cursor.fetchone()[0])
