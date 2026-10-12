from decimal import Decimal

from shop.models import Product

from .services import CartResult


CART_SESSION_ID = "cart"

POST_PRICE_LOW = Decimal("100000")
POST_PRICE_HIGH = Decimal("200000")


class Cart:

    def __init__(self, request):

        self.session = request.session

        cart = self.session.get(
            CART_SESSION_ID
        )

        if cart is None:

            cart = {}

            self.session[CART_SESSION_ID] = cart

        self._cart = cart

    # ==============================
    # Session
    # ==============================

    def _save(self):

        self.session.modified = True

    # ==============================
    # Helpers
    # ==============================

    def has_product(self, product):

        return str(product.id) in self._cart

    def get_item(self, product):

        return self._cart.get(
            str(product.id)
        )

    def get_quantity(self, product):

        item = self.get_item(product)

        if not item:

            return 0

        return item["quantity"]

    # ==============================
    # Add
    # ==============================

    def add(
        self,
        product,
        quantity=1
    ):

        if not product.is_active:

            return CartResult(
                False,
                "محصول فعال نیست."
            )

        if product.inventory <= 0:

            return CartResult(
                False,
                "محصول موجود نیست."
            )

        if quantity <= 0:

            return CartResult(
                False,
                "تعداد نامعتبر است."
            )

        current_quantity = self.get_quantity(
            product
        )

        new_quantity = (
            current_quantity
            +
            quantity
        )

        if new_quantity > product.inventory:

            new_quantity = product.inventory

        self._cart[
            str(product.id)
        ] = {

            "quantity": new_quantity

        }

        self._save()

        return CartResult(
            True,
            "محصول به سبد خرید اضافه شد."
        )

    # ==============================
    # Decrease
    # ==============================

    def decrease(
        self,
        product,
        quantity=1
    ):

        if not self.has_product(product):

            return CartResult(
                False,
                "محصول در سبد خرید وجود ندارد."
            )

        current_quantity = self.get_quantity(
            product
        )

        current_quantity -= quantity

        if current_quantity <= 0:

            del self._cart[
                str(product.id)
            ]

        else:

            self._cart[
                str(product.id)
            ][
                "quantity"
            ] = current_quantity

        self._save()

        return CartResult(
            True,
            "سبد خرید بروزرسانی شد."
        )

    # ==============================
    # Remove
    # ==============================

    def remove(self, product):

        if not self.has_product(product):

            return CartResult(
                False,
                "محصول در سبد وجود ندارد."
            )

        del self._cart[
            str(product.id)
        ]

        self._save()

        return CartResult(
            True,
            "محصول حذف شد."
        )

    # ==============================
    # Clear
    # ==============================

    def clear(self):

        self.session.pop(
            CART_SESSION_ID,
            None
        )
        self._cart = {}
        self._save()

    # ==============================
    # Clean Cart
    # ==============================

    def clean(self):
        """
        هماهنگ سازی سبد خرید با دیتابیس
        """

        if not self._cart:

            return

        products = Product.objects.filter(
            id__in=self._cart.keys(),
            is_active=True
        )

        valid_products = {

            str(product.id): product

            for product in products

        }

        changed = False

        for product_id in list(
            self._cart.keys()
        ):

            # محصول حذف شده یا غیرفعال

            if product_id not in valid_products:

                del self._cart[product_id]

                changed = True

                continue

            product = valid_products[
                product_id
            ]

            quantity = self._cart[
                product_id
            ]["quantity"]

            # موجودی صفر

            if product.inventory <= 0:

                del self._cart[
                    product_id
                ]

                changed = True

                continue

            # بیشتر از موجودی

            if quantity > product.inventory:

                self._cart[
                    product_id
                ][
                    "quantity"
                ] = product.inventory

                changed = True

            # تعداد غیر معتبر

            if quantity <= 0:

                del self._cart[
                    product_id
                ]

                changed = True

        if changed:

            self._save()

    # ==============================
    # Validate Before Order
    # ==============================

    def validate(self):

        errors = []

        products = Product.objects.filter(
            id__in=self._cart.keys()
        )

        products_dict = {

            str(product.id): product

            for product in products

        }

        for product_id, item in self._cart.items():

            if product_id not in products_dict:

                errors.append(
                    "یکی از محصولات حذف شده است."
                )

                continue

            product = products_dict[
                product_id
            ]

            if not product.is_active:

                errors.append(
                    f"{product.name} فعال نیست."
                )

            elif product.inventory < item["quantity"]:

                errors.append(
                    f"موجودی {product.name} کافی نیست."
                )

        return {

            "valid": len(errors) == 0,

            "errors": errors

        }

    # ==============================
    # Price
    # ==============================

    def get_subtotal_price(self):

        return sum(

            item["total_price"]

            for item in self

        )

    def get_post_price(self):

        total_weight = sum(

            item["product"].weight
            *
            item["quantity"]

            for item in self

        )

        if total_weight <= 1000:
            return POST_PRICE_LOW

        return POST_PRICE_HIGH

    def get_total_price(self):

        return (

            self.get_subtotal_price()

            +

            self.get_post_price()

        )

    @property
    def is_empty(self):
        """
        بررسی خالی بودن سبد خرید
        """
        return len(self) == 0
    
    def get_total_discount(self):
        """
        مجموع تخفیف محصولات داخل سبد
        """

        total_discount = Decimal("0")

        for item in self:

            discount = (
                item["product"].price
                -
                item["product"].final_price
            )

            total_discount += (
                discount
                *
                item["quantity"]
            )

        return total_discount
    # ==============================
    # Summary
    # ==============================

    def summary(self):

        return {

            "item_count": len(self),

            "subtotal": str(
                self.get_subtotal_price()
            ),

            "discount": str(
                self.get_total_discount()
            ),

            "post_price": str(
                self.get_post_price()
            ),

            "total_price": str(
                self.get_total_price()
            ),

            "is_empty": self.is_empty,

        }

    # ==============================
    # Python Methods
    # ==============================

    def __len__(self):

        return sum(

            item["quantity"]

            for item in self._cart.values()

        )

    def __iter__(self):

        product_ids = self._cart.keys()

        products = (
            Product.objects
            .filter(
                id__in=product_ids,
                is_active=True
            )
            .select_related(
                "category"
            )
            .prefetch_related(
                "images",
                "features",
            )
        )

        cart_copy = self._cart.copy()

        for product in products:

            item = cart_copy[
                str(product.id)
            ].copy()   # مهم: کپی داخلی

            item["product"] = product

            item["price"] = product.final_price

            item["total_price"] = (
                item["price"]
                *
                item["quantity"]
            )

            yield item
