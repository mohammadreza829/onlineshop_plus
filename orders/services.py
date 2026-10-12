from django.db import transaction
from shop.models import Product
from .models import Order, OrderItem
from django.conf import settings
from zarinpal import ZarinPal, Config


class OrderCreationError(Exception):
    pass


@transaction.atomic
def create_order_from_cart(cart, cleaned_data, user):
    cart.clean()

    if cart.is_empty:
        raise OrderCreationError("سبد خرید خالی است.")

    validation = cart.validate()
    if not validation["valid"]:
        raise OrderCreationError("\n".join(validation["errors"]))

    # ۱. قفل کردن محصولات جهت چک کردن موجودی
    product_ids = [item["product"].id for item in cart]
    locked_products = {
        product.id: product
        for product in Product.objects.select_for_update().filter(id__in=product_ids)
    }

    # ۲. ایجاد سفارش
    order = Order.objects.create(
        user=user,
        first_name=cleaned_data["first_name"],
        last_name=cleaned_data["last_name"],
        phone=cleaned_data["phone"],
        address=cleaned_data["address"],
        postal_code=cleaned_data["postal_code"],
        post_price=cart.get_post_price(),
        total_price=0,
    )

    # ۳. ایجاد آیتم‌های سفارش (بدون کسر انبار در این مرحله)
    for item in cart:
        product = locked_products.get(item["product"].id)

        if product is None:
            raise OrderCreationError("یکی از محصولات حذف شده است.")

        quantity = item["quantity"]
        if product.inventory < quantity:
            raise OrderCreationError(f"موجودی «{product.name}» کافی نیست.")

        price = item["price"]
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=product.sku,
            price=price,
            quantity=quantity,
            total_price=price * quantity,
        )

    # ۴. محاسبه مبلغ نهایی
    order.total_price = order.calculate_total()
    order.save(update_fields=["total_price"])

    return order


def get_zarinpal():
    config = Config(
        merchant_id=settings.ZARINPAL["merchant_id"],
        sandbox=settings.ZARINPAL["sandbox"],
    )
    return ZarinPal(config)


@transaction.atomic
def decrease_stock(order):
    """
    کسر موجودی انبار پس از تایید پرداخت
    """
    if order.stock_updated:
        return

    for item in order.items.select_for_update():
        if item.product:
            if item.product.inventory < item.quantity:
                raise ValueError(
                    f"موجودی محصول {item.product_name} کافی نیست.")

            item.product.inventory -= item.quantity
            item.product.save(update_fields=["inventory"])

    order.stock_updated = True
    order.save(update_fields=["stock_updated"])
