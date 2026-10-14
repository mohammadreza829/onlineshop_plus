"""Seed an EMPTY, explicit local benchmark DB. Never touches the normal shop database."""

import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from account.models import ShopUser
from shop.models import Category, Product, ProductVariant, Review
from shop.recommendations import invalidate_recommendations


class Command(BaseCommand):
    help = "Create synthetic products in a dedicated empty _benchmark PostgreSQL database"

    def add_arguments(self, parser):
        parser.add_argument("--products", type=int, default=10000)
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        if (
            not settings.DEBUG
            or not getattr(settings, "BENCHMARK_ALLOW_SEED", False)
            or not str(connection.settings_dict["NAME"]).endswith("_benchmark")
        ):
            raise CommandError("Requires onlineshop.loadtest_settings and a dedicated _benchmark database")
        if connection.vendor != "postgresql":
            raise CommandError("PostgreSQL required")
        total = options["products"]
        if not 100 <= total <= 100000:
            raise CommandError("Product count must be 100..100000")
        if Product.objects.exists() or Category.objects.exists():
            raise CommandError(
                "Benchmark DB must be empty; command is intentionally not a destructive reseed"
            )
        output = Path(options["output"])
        if output.exists():
            raise CommandError("Output file already exists")
        with transaction.atomic():
            categories = Category.objects.bulk_create(
                [Category(name=f"دسته آزمایشی {i}", slug=f"benchmark-category-{i}") for i in range(100)]
            )
            kinds = ["کفش", "کیف", "کتاب", "چراغ", "پوشاک"]
            products = Product.objects.bulk_create(
                [
                    Product(
                        category=categories[i % 100],
                        sku=f"BENCH-{i}",
                        slug=f"benchmark-{i}",
                        name=f"{kinds[i % 5]} آزمایشی شماره {i}",
                        description="داده مصنوعی مخصوص آزمون، نه کالای واقعی. "
                        + ("نایاب " if i % 250 == 0 else "")
                        + "رنگ آبی",
                        price=Decimal(100000 + (i % 50) * 1000),
                        inventory=25 if i % 10 else 0,
                        weight=500,
                    )
                    for i in range(total)
                ],
                batch_size=500,
            )
            choices = ProductVariant.objects.bulk_create(
                [
                    ProductVariant(
                        product=p,
                        sku=f"BV-{p.pk}-{color}",
                        color=color,
                        size="M",
                        price=p.price + 1000,
                        inventory=7,
                    )
                    for i, p in enumerate(products)
                    if i % 4 == 0
                    for color in ["آبی", "قرمز"]
                ],
                batch_size=500,
            )
            user = ShopUser.objects.create_user(phone="09129999999", password=None)
            reviews = Review.objects.bulk_create(
                [
                    Review(
                        product=p,
                        user=user,
                        rating=1 + i % 5,
                        text="نظر مصنوعی benchmark",
                        status=Review.APPROVED,
                    )
                    for i, p in enumerate(products)
                    if i % 2 == 0
                ],
                batch_size=500,
            )
        invalidate_recommendations()
        with connection.cursor() as cursor:
            for table in ["shop_product", "shop_productvariant", "shop_review"]:
                cursor.execute(f'VACUUM (ANALYZE) "{table}"')
        metadata = {
            "synthetic_only": True,
            "products": len(products),
            "variants": len(choices),
            "approved_reviews": len(reviews),
            "categories": len(categories),
            "anchor_slug": products[1].slug,
            "database": str(connection.settings_dict["NAME"]),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        self.stdout.write(f"Created {len(products)} synthetic products; metadata saved (no provider calls)")
