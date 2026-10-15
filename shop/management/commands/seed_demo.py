"""Offline, additive catalogue fixtures for the isolated laptop database only."""

from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFilter

from orders.models import Coupon
from shop.models import Category, Product, ProductFeatures, ProductImage, ProductVariant

CATEGORIES = [
    ("shirts", "پیراهن", "shirt"),
    ("tees", "تیشرت", "tee"),
    ("trousers", "شلوار", "trousers"),
    ("jackets", "کت", "jacket"),
    ("hoodies", "هودی", "hoodie"),
    ("skirts", "دامن", "skirt"),
]
STYLES = ["روزمره", "مینیمال", "شهری", "آزاد", "کلاسیک", "استودیو"]
COLORS = [("کرم", "#c5b69b"), ("زیتونی", "#727b62"), ("سرمه‌ای", "#475565"), ("آجری", "#ae7762")]


def illustration(kind, color, number):
    """Synthetic garment illustration, not a photograph of a real item."""
    image = Image.new("RGB", (800, 1067), "#ecebe5")
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((40, 40, 760, 1027), radius=30, fill="#f4f3ee")
    d.ellipse((180, 850, 620, 910), fill="#deddd5")
    layer = Image.new("RGBA", image.size)
    g = ImageDraw.Draw(layer)
    if kind == "trousers":
        points = [(245, 240), (555, 240), (595, 840), (425, 840), (400, 480), (375, 840), (205, 840)]
    elif kind == "skirt":
        points = [(285, 290), (515, 290), (650, 825), (150, 825)]
    else:
        points = [
            (300, 275),
            (350, 250),
            (450, 250),
            (500, 275),
            (650, 385),
            (570, 510),
            (510, 470),
            (525, 800),
            (275, 800),
            (290, 470),
            (230, 510),
            (150, 385),
        ]
    shadow = Image.new("RGBA", image.size)
    ImageDraw.Draw(shadow).polygon([(x + 10, y + 18) for x, y in points], fill=(30, 35, 25, 45))
    image = Image.alpha_composite(image.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(15)))
    g.polygon(points, fill=color, outline="#555b50", width=3)
    if kind in ("shirt", "jacket"):
        g.polygon([(350, 250), (400, 305), (355, 375), (315, 275)], fill="#e6dfd0", outline="#6d7064")
        g.polygon([(450, 250), (400, 305), (445, 375), (485, 275)], fill="#e6dfd0", outline="#6d7064")
        g.line((400, 308, 400, 790), fill="#555b50", width=3)
        for y in range(400, 760, 65):
            g.ellipse((394, y, 402, y + 8), fill="#f1ede2")
        g.rectangle((430, 415, 490, 485), outline="#626858", width=3)
    elif kind in ("tee", "hoodie"):
        g.arc((345, 222, 455, 330), 0, 180, fill="#e9e4d7", width=14)
        g.line((290, 780, 510, 780), fill="#626858", width=4)
        if kind == "hoodie":
            g.rounded_rectangle((325, 625, 475, 735), radius=24, outline="#626858", width=4)
            g.line((370, 320, 365, 420), fill="#e9e4d7", width=4)
            g.line((430, 320, 435, 420), fill="#e9e4d7", width=4)
    elif kind == "trousers":
        g.line((250, 275, 550, 275), fill="#626858", width=6)
        g.line((400, 280, 400, 460), fill="#626858", width=3)
        g.arc((240, 280, 365, 420), 0, 90, fill="#626858", width=3)
        g.arc((435, 280, 560, 420), 90, 180, fill="#626858", width=3)
    else:
        for x in range(320, 500, 40):
            g.line((x, 310, x + (x - 400) // 2, 800), fill="#626858", width=2)
        g.line((285, 310, 515, 310), fill="#626858", width=5)
    image = Image.alpha_composite(image, layer)
    d = ImageDraw.Draw(image)
    d.text((75, 80), "STUDIO / DEMO", fill="#50594e", font_size=24)
    d.text((75, 963), f"ILLUSTRATION     /     {number:02d}", fill="#50594e", font_size=20)
    output = BytesIO()
    image.convert("RGB").save(output, "WEBP", quality=88)
    return output.getvalue()


class Command(BaseCommand):
    help = "Add 36 catalogue products to the isolated laptop DB; normalize legacy demo name suffixes only."

    def handle(self, *args, **options):
        actual = connection.settings_dict["NAME"]
        expected = getattr(settings, "DEMO_DATABASE_PATH", "")
        if not (
            settings.DEBUG
            and getattr(settings, "LOCAL_DEMO_MODE", False)
            and connection.vendor == "sqlite"
            and expected
            and str(actual) != ":memory:"
            and Path(actual).resolve() == Path(expected).resolve()
        ):
            raise CommandError("Use python manage_laptop.py seed_demo on the isolated laptop SQLite DB only.")
        # Check ALL name collisions before writing anything; never claim ownership of real data.
        coupon = Coupon.objects.filter(code="DEMO10").first()
        if coupon and (coupon.kind != Coupon.PERCENT or coupon.value != 10):
            raise CommandError("DEMO10 already exists with different terms; no data changed.")
        for ci, (slug, name, _kind) in enumerate(CATEGORIES):
            category = Category.objects.filter(slug=f"demo-{slug}").first()
            if category and category.name not in (name, f"{name} (دمو)"):
                raise CommandError(f"Category collision: demo-{slug}; no data changed.")
            for j in range(6):
                sku = f"LAPTOP-DEMO-{ci + 1:02d}-{j + 1:02d}"
                product_slug = f"demo-{slug}-{j + 1}"
                existing = Product.objects.filter(sku=sku).first()
                if (existing and existing.slug != product_slug) or Product.objects.filter(
                    slug=product_slug
                ).exclude(sku=sku).exists():
                    raise CommandError(f"Product collision: {sku}; no data changed.")
        files = []
        created = 0
        renamed = 0
        timestamp = timezone.now()
        try:
            with transaction.atomic():
                for ci, (slug, name, kind) in enumerate(CATEGORIES):
                    category, _ = Category.objects.get_or_create(slug=f"demo-{slug}", defaults={"name": name})
                    # Only normalize the exact old seed label; never rewrite custom names.
                    renamed += Category.objects.filter(pk=category.pk, name=f"{name} (دمو)").update(name=name)
                    for j, style in enumerate(STYLES):
                        sku = f"LAPTOP-DEMO-{ci + 1:02d}-{j + 1:02d}"
                        price = 390000 + ci * 95000 + j * 45000
                        product, fresh = Product.objects.get_or_create(
                            sku=sku,
                            defaults={
                                "slug": f"demo-{slug}-{j + 1}",
                                "category": category,
                                "name": f"{name} {style}",
                                "price": price,
                                "off": [0, 10, 0, 20, 0, 0][j],
                                "inventory": 0 if j == 5 else 18,
                                "description": "محصول صرفاً نمایشی برای تست روی لپ‌تاپ است. قیمت، موجودی و مشخصات ساختگی‌اند؛ برای فروش واقعی نیست. تصویر، طرح شماتیک تولیدشده است و عکس کالای واقعی نیست.",
                            },
                        )
                        if not fresh:
                            renamed += Product.objects.filter(
                                pk=product.pk, name=f"{name} {style} (دمو)"
                            ).update(name=f"{name} {style}")
                            continue  # Preserve other edits, sold stock and deleted/replaced images.
                        created += 1
                        # Interleave categories in newest-first lists, rather than
                        # filling the home page with only the last seeded category.
                        Product.objects.filter(pk=product.pk).update(
                            created=timestamp - timedelta(minutes=j * len(CATEGORIES) + ci)
                        )
                        color_name, color_hex = COLORS[(ci + j) % len(COLORS)]
                        if j >= 2:
                            for color_index, color in enumerate([color_name, "مشکی"]):
                                for size_index, size in enumerate(["M", "L"]):
                                    ProductVariant.objects.create(
                                        product=product,
                                        sku=f"{sku}-{color_index}-{size_index}",
                                        color=color,
                                        size=size,
                                        price=price + size_index * 30000,
                                        inventory=0
                                        if j == 5 or (color_index == 1 and size_index == 1)
                                        else 12,
                                    )
                        ProductFeatures.objects.create(
                            product=product,
                            name="نوع داده",
                            value="دموی ساختگی؛ غیرقابل فروش",
                        )
                        ProductFeatures.objects.create(product=product, name="فرم نمایشی", value=style)
                        image = ProductImage(
                            product=product,
                            is_primary=True,
                            description="تصویر شماتیک دمو؛ نه عکس محصول واقعی",
                        )
                        image.image.save(
                            f"{sku.lower()}.webp",
                            ContentFile(illustration(kind, color_hex, ci * 6 + j + 1)),
                            save=False,
                        )
                        files.append((image.image.storage, image.image.name))
                        image.save()
                Coupon.objects.get_or_create(
                    code="DEMO10",
                    defaults={
                        "kind": Coupon.PERCENT,
                        "value": 10,
                        "per_user_limit": 100,
                    },
                )
        except Exception:
            for storage, name in files:
                storage.delete(name)
            raise
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo ready: {created} new products; {renamed} legacy names normalized. "
                "Other existing product data unchanged. Coupon: DEMO10 (10%)."
            )
        )
        self.stdout.write(
            "Synthetic catalogue only. Real SMS and payment are disabled in the laptop profile."
        )
