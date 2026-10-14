"""Shared factories / fakes for the test-suite (no extra dependencies)."""

import itertools
from decimal import Decimal

from account.models import ShopUser
from addresses.models import Address
from payment.gateway import RequestResult, VerifyResult, VerifyStatus
from shop.models import Category, Product

_seq = itertools.count(1)


def make_user(phone=None, **extra):
    phone = phone or f"0912{next(_seq):07d}"
    return ShopUser.objects.create_user(phone=phone, password=None, **extra)


def make_product(inventory=10, price=100_000, off=0, **extra):
    n = next(_seq)
    category, _ = Category.objects.get_or_create(slug="cat", defaults={"name": "cat"})
    return Product.objects.create(
        category=category,
        sku=f"SKU-{n}",
        name=f"Product {n}",
        slug=f"product-{n}",
        price=Decimal(price),
        off=off,
        inventory=inventory,
        weight=500,
        **extra,
    )


def make_address(user):
    return Address.objects.create(
        user=user,
        title="خانه",
        receiver_name="علی رضایی",
        receiver_phone=user.phone,
        province="tehran",
        city="تهران",
        full_address="خیابان آزادی، پلاک ۱",
        postal_code="1234567890",
    )


class FakeCart:
    """Minimal stand-in for cart.Cart, used by service-level tests."""

    def __init__(self, items, post_price=Decimal("100000")):
        self._items = items  # list of (product, quantity)
        self._post_price = post_price

    def clean(self):
        pass

    @property
    def is_empty(self):
        return not self._items

    def validate(self):
        return {"valid": True, "errors": []}

    def get_post_price(self):
        return self._post_price

    def __iter__(self):
        for product, quantity in self._items:
            yield {"product": product, "quantity": quantity, "price": product.final_price}


class FakeGateway:
    """Records calls; configure `verify_status` / `request_ok` per test."""

    def __init__(self, verify_status=VerifyStatus.SUCCESS, request_ok=True, ref_id="REF-1"):
        self.verify_status = verify_status
        self.request_ok = request_ok
        self.ref_id = ref_id
        self.verify_calls = 0
        self.request_calls = 0
        self._authorities = (f"A{n:035d}" for n in itertools.count(1))

    def request_payment(self, amount_toman, description, callback_url, mobile=""):
        self.request_calls += 1
        if not self.request_ok:
            return RequestResult(ok=False, code=-9, error="rejected")
        authority = next(self._authorities)
        return RequestResult(
            ok=True, authority=authority, payment_url=f"https://gw.test/StartPay/{authority}", code=100
        )

    def verify(self, amount_toman, authority):
        self.verify_calls += 1
        if self.verify_status == VerifyStatus.SUCCESS:
            return VerifyResult(
                status=VerifyStatus.SUCCESS, ref_id=self.ref_id, card_pan="6037****1234", code=100
            )
        code = -51 if self.verify_status == VerifyStatus.FAILED else None
        return VerifyResult(status=self.verify_status, code=code)
