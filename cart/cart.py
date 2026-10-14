from decimal import Decimal

from django.conf import settings

from shop.models import Product

from .services import MAX_QUANTITY_PER_REQUEST, CartResult

CART_SESSION_ID = "cart"
POST_PRICE_LOW = Decimal("100000")
POST_PRICE_HIGH = Decimal("200000")


class Cart:
    def __init__(self, request):
        self._entries_cache = None
        self.session = request.session
        self._cart = self.session.setdefault(CART_SESSION_ID, {})
        if not isinstance(self._cart, dict):
            self._cart = {}
            self._save()

    def _save(self):
        self._entries_cache = None
        self.session[CART_SESSION_ID] = self._cart
        self.session.modified = True

    @staticmethod
    def _key(product, variant=None):
        return f"{product.pk}:{variant.pk}" if variant else str(product.pk)

    def has_product(self, product, variant=None):
        return self._key(product, variant) in self._cart

    def get_item(self, product, variant=None):
        return self._cart.get(self._key(product, variant))

    def get_quantity(self, product, variant=None):
        return (self.get_item(product, variant) or {}).get("quantity", 0)

    @staticmethod
    def _valid(product, variant):
        if not product.is_active:
            return False
        if variant:
            return variant.product_id == product.pk and variant.is_active and variant.inventory > 0
        return not product.variants.exists() and product.inventory > 0

    def add(self, product, quantity=1, variant=None):
        if not self._valid(product, variant):
            return CartResult(False, "محصول موجود نیست یا انتخاب رنگ/سایز الزامی است.")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            return CartResult(False, "تعداد نامعتبر است.")
        if not self.has_product(product, variant) and len(self._cart) >= settings.CART_MAX_LINES:
            return CartResult(False, "سبد خرید به سقف تعداد ردیف رسیده است.")
        stock = variant.inventory if variant else product.inventory
        self._cart[self._key(product, variant)] = {
            "quantity": min(self.get_quantity(product, variant) + quantity, stock)
        }
        self._save()
        return CartResult(True, "محصول به سبد خرید اضافه شد.")

    def set_quantity(self, product, quantity, variant=None):
        """Set an existing line, not add to it. Zero removes; retries are idempotent."""
        if (
            not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or not 0 <= quantity <= MAX_QUANTITY_PER_REQUEST
        ):
            return CartResult(False, "تعداد نامعتبر است.")
        if quantity == 0:
            return self.remove(product, variant) if self.has_product(product, variant) else CartResult(True)
        if not self.has_product(product, variant):
            return CartResult(False, "محصول در سبد وجود ندارد.", data={"missing": True})
        if not self._valid(product, variant):
            return CartResult(False, "محصول موجود نیست یا انتخاب رنگ/سایز معتبر نیست.")
        stock = variant.inventory if variant else product.inventory
        self._cart[self._key(product, variant)] = {"quantity": min(quantity, stock)}
        self._save()
        return CartResult(True, "تعداد بروزرسانی شد.")

    def decrease(self, product, quantity=1, variant=None):
        if quantity <= 0 or not self.has_product(product, variant):
            return CartResult(False, "محصول در سبد خرید وجود ندارد یا تعداد نامعتبر است.")
        key = self._key(product, variant)
        remaining = self.get_quantity(product, variant) - quantity
        if remaining <= 0:
            del self._cart[key]
        else:
            self._cart[key]["quantity"] = remaining
        self._save()
        return CartResult(True, "سبد خرید بروزرسانی شد.")

    def remove(self, product, variant=None):
        key = self._key(product, variant)
        if key not in self._cart:
            return CartResult(False, "محصول در سبد وجود ندارد.")
        del self._cart[key]
        self._save()
        return CartResult(True, "محصول حذف شد.")

    def clear(self):
        self._entries_cache = None
        self.session.pop(CART_SESSION_ID, None)
        self._cart = {}
        self.session.modified = True

    def _resolved(self):
        if self._entries_cache is None:
            self._entries_cache = list(self._load_entries())
        return iter(self._entries_cache)

    def _load_entries(self):
        ids = {int(k.split(":")[0]) for k in self._cart if k.split(":")[0].isdigit()}
        products = {
            p.pk: p
            for p in Product.objects.filter(pk__in=ids)
            .select_related("category")
            .prefetch_related("variants")
        }
        for key, item in list(self._cart.items()):
            try:
                parts = key.split(":")
                if len(parts) not in (1, 2):
                    raise ValueError
                product = products[int(parts[0])]
                variants = {v.pk: v for v in product.variants.all()}
                variant = variants[int(parts[1])] if len(parts) == 2 else None
                qty = item["quantity"]
                if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                    raise ValueError
                valid = product.is_active and (variant.is_active if variant else not variants)
                if not valid:
                    raise ValueError
                if variant:
                    variant.product = product
                yield key, product, variant, qty
            except (KeyError, ValueError, TypeError, AttributeError):
                yield key, None, None, 0

    def clean(self):
        changed = False
        for key, product, _variant, _qty in self._resolved():
            if product is None:
                self._cart.pop(key, None)
                changed = True
            # Retain requested quantity; checkout validates availability without silent loss.
        if changed:
            self._save()

    def validate(self):
        errors = []
        for _key, product, variant, qty in self._resolved():
            if product is None or qty > (variant.inventory if variant else product.inventory):
                errors.append("محصول نامعتبر است یا موجودی کافی نیست.")
        return {"valid": not errors, "errors": errors}

    def get_subtotal_price(self):
        return sum((item["total_price"] for item in self), Decimal("0"))

    def get_post_price(self):
        if self.is_empty:
            return Decimal("0")
        weight = sum(item["product"].weight * item["quantity"] for item in self)
        return POST_PRICE_LOW if weight <= 1000 else POST_PRICE_HIGH

    def get_total_price(self):
        return self.get_subtotal_price() + self.get_post_price()

    def get_total_discount(self):
        return sum(
            ((item["variant"] or item["product"]).price - item["price"]) * item["quantity"] for item in self
        )

    @property
    def is_empty(self):
        return len(self) == 0

    def summary(self):
        return {
            "item_count": len(self),
            "subtotal": str(self.get_subtotal_price()),
            "discount": str(self.get_total_discount()),
            "post_price": str(self.get_post_price()),
            "total_price": str(self.get_total_price()),
            "is_empty": self.is_empty,
        }

    def __len__(self):
        return sum(
            item.get("quantity", 0)
            for item in self._cart.values()
            if isinstance(item, dict)
            and isinstance(item.get("quantity"), int)
            and not isinstance(item["quantity"], bool)
            and item["quantity"] > 0
        )

    def __iter__(self):
        for _key, product, variant, quantity in self._resolved():
            if product is None:
                continue
            price = (variant or product).final_price
            yield {
                "product": product,
                "variant": variant,
                "quantity": quantity,
                "price": price,
                "total_price": price * quantity,
            }
