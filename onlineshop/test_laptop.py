import json
import os
import subprocess
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings

from account.sms import send_otp
from api.serializers import ProductSerializer
from orders.models import Coupon
from payment.gateway import DisabledLocalGateway, VerifyStatus, ZarinpalGateway, get_gateway
from shop.models import Category, Product, ProductImage, ProductVariant
from shop.selectors import catalog_products


class LaptopProfileTests(SimpleTestCase):
    def test_stale_production_env_cannot_enable_external_services(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {
                **os.environ,
                "LAPTOP_DATA_DIR": directory,
                "DJANGO_DEBUG": "false",
                "DJANGO_DB_ENGINE": "postgresql",
                "SMS_BACKEND": "smsir",
                "SMS_IR_API_KEY": "",
                "SMS_ASYNC": "true",
                "CACHE_URL": "redis://unreachable.invalid:6379/0",
            }
            script = (
                "import json; import onlineshop.laptop_settings as s; "
                "print(json.dumps([s.DEBUG,s.SMS_BACKEND,s.SMS_ASYNC,"
                "s.DATABASES['default']['ENGINE'],str(s.DATABASES['default']['NAME']),"
                "s.CACHES['default']['BACKEND'],s.LOCAL_PAYMENT_DISABLED]))"
            )
            result = subprocess.run(
                [os.sys.executable, "-c", script],
                env=env,
                cwd=Path(__file__).resolve().parent.parent,
                capture_output=True,
                text=True,
                check=True,
            )
            values = json.loads(result.stdout)
            self.assertEqual(values[:4], [True, "console", False, "django.db.backends.sqlite3"])
            self.assertEqual(Path(values[4]), Path(directory) / "laptop.sqlite3")
            self.assertIn("LocMemCache", values[5])
            self.assertTrue(values[6])
            self.assertGreater(len((Path(directory) / "django-secret").read_text()), 32)
            env["DJANGO_SETTINGS_MODULE"] = "onlineshop.laptop_settings"
            logged = subprocess.run(
                [
                    os.sys.executable,
                    "-c",
                    "import django; django.setup(); from account.sms import send_otp; "
                    "send_otp('09120000000', '654321')",
                ],
                env=env,
                cwd=Path(__file__).resolve().parent.parent,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("LOCAL DEVELOPMENT ONLY", logged.stderr)
            self.assertIn("654321", logged.stderr)
            self.assertNotIn("[SIX_DIGIT_VALUE]", logged.stderr)

    @override_settings(DEBUG=True, SMS_BACKEND="console", SMS_ASYNC=False)
    @patch("account.sms.requests.post")
    def test_console_otp_does_not_send_http(self, post):
        with self.assertLogs("account.sms", level="WARNING") as messages:
            send_otp("09120000000", "654321")
        post.assert_not_called()
        self.assertIn("654321", messages.output[0])

    @override_settings(DEBUG=True, LOCAL_PAYMENT_DISABLED=True)
    @patch("payment.gateway.requests.post")
    def test_local_payment_never_calls_or_approves_gateway(self, post):
        gateway = get_gateway()
        self.assertIsInstance(gateway, DisabledLocalGateway)
        self.assertFalse(gateway.request_payment(100, "demo", "http://127.0.0.1/").ok)
        self.assertEqual(gateway.verify(100, "demo").status, VerifyStatus.UNKNOWN)
        post.assert_not_called()

    @override_settings(DEBUG=False, LOCAL_PAYMENT_DISABLED=True)
    def test_production_cannot_use_disabled_local_gateway(self):
        self.assertIsInstance(get_gateway(), ZarinpalGateway)


class CatalogImageTests(TestCase):
    def test_thumbnail_prefers_primary_then_order_and_is_null_when_absent(self):
        with override_settings(MEDIA_URL="/media/"):
            product = Product.objects.create(sku="IMAGE", slug="image", name="Image", price=1)
            self.assertIsNone(ProductSerializer(catalog_products().get(pk=product.pk)).data["image"])
            ProductImage.objects.create(product=product, image="products/fallback.webp", order=0)
            primary = ProductImage.objects.create(
                product=product, image="products/primary.webp", order=4, is_primary=True
            )
            self.assertEqual(
                ProductSerializer(catalog_products().get(pk=product.pk)).data["image"],
                "/media/products/primary.webp",
            )
            primary.is_primary = False
            primary.save()
            self.assertEqual(
                ProductSerializer(catalog_products().get(pk=product.pk)).data["image"],
                "/media/products/fallback.webp",
            )


@skipUnless(connection.vendor == "sqlite", "Laptop fixture tests target SQLite only")
class DemoSeedTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(
            DEBUG=True,
            LOCAL_DEMO_MODE=True,
            DEMO_DATABASE_PATH=connection.settings_dict["NAME"],
            MEDIA_ROOT=self.media.name,
        )
        self.override.enable()
        self.addCleanup(self.override.disable)

    def seed(self):
        with redirect_stdout(StringIO()):
            call_command("seed_demo")

    def test_additive_seed_and_images_and_preserve_inventory_on_rerun(self):
        original = Product.objects.create(
            sku="REAL-KEEP", slug="real-keep", name="Existing", price=42, inventory=7
        )
        self.seed()
        self.assertEqual(Category.objects.filter(slug__startswith="demo-").count(), 6)
        self.assertEqual(Product.objects.filter(sku__startswith="LAPTOP-DEMO-").count(), 36)
        self.assertEqual(ProductVariant.objects.count(), 96)
        self.assertEqual(ProductImage.objects.count(), 36)
        with self.assertNumQueries(1):
            serialized = ProductSerializer(catalog_products(), many=True).data
        demos = [item for item in serialized if item["sku"].startswith("LAPTOP-DEMO-")]
        self.assertTrue(all(item["image"].startswith("/media/products/") for item in demos))
        self.assertTrue(Coupon.objects.filter(code="DEMO10", value=10).exists())
        first = Product.objects.get(sku="LAPTOP-DEMO-01-01")
        first.inventory = 3
        first.save()
        image = first.images.get(is_primary=True)
        from PIL import Image

        with image.image.open("rb") as handle, Image.open(handle) as rendered:
            self.assertEqual(rendered.size, (800, 1067))
            self.assertEqual(rendered.format, "WEBP")
        self.seed()
        first.refresh_from_db()
        original.refresh_from_db()
        self.assertEqual(first.inventory, 3)
        self.assertEqual(original.inventory, 7)
        self.assertEqual(Product.objects.count(), 37)
        self.assertEqual(ProductImage.objects.count(), 36)

    @override_settings(LOCAL_DEMO_MODE=False)
    def test_refuses_nonlocal_profile(self):
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(Product.objects.count(), 0)

    def test_collision_does_not_touch_existing_data(self):
        Product.objects.create(sku="REAL", slug="demo-shirts-1", name="Keep", price=99)
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Category.objects.count(), 0)

    def test_coupon_collision_is_not_overwritten(self):
        Coupon.objects.create(code="DEMO10", kind=Coupon.FIXED, value=500)
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(Product.objects.count(), 0)
