from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from addresses.selectors import addresses_for_user
from cart.cart import Cart
from payment.views import redirect_to_gateway

from .selectors import orders_for_user
from .services import (
    OrderActionError,
    OrderCreationError,
    cancel_order_by_customer,
    create_order_from_cart,
    expire_order_if_needed,
)


@login_required
def order_create(request):
    """
    Checkout: choose an address -> order is created and stock reserved for
    ORDER_RESERVATION_MINUTES -> redirect to the payment gateway.
    """
    cart = Cart(request)
    if cart.is_empty:
        messages.warning(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    user_addresses = addresses_for_user(request.user)
    context = {"cart": cart, "addresses": user_addresses}

    if request.method != "POST":
        return render(request, "orders/create_order.html", context)

    address_id = request.POST.get("address_id")
    if not address_id or not str(address_id).isdigit():
        messages.error(request, "لطفاً یک آدرس برای ارسال سفارش انتخاب کنید.")
        return render(request, "orders/create_order.html", context)

    selected_address = get_object_or_404(addresses_for_user(request.user), id=address_id)

    try:
        order = create_order_from_cart(cart, selected_address, request.user)
    except OrderCreationError as exc:
        messages.error(request, str(exc))
        return redirect("cart:cart_detail")

    return redirect_to_gateway(request, order)


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(orders_for_user(request.user), id=order_id)
    if expire_order_if_needed(order):
        order.refresh_from_db()
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def order_list(request):
    orders = orders_for_user(request.user)
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
@require_POST
def order_cancel(request, order_id):
    order = get_object_or_404(orders_for_user(request.user), id=order_id)
    if not order.is_cancelable_by_user:
        messages.error(request, "این سفارش قابل لغو نیست.")
        return redirect("orders:order_detail", order_id=order.id)
    try:
        cancel_order_by_customer(order, request.user)
    except OrderActionError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "سفارش لغو شد.")
    return redirect("orders:order_detail", order_id=order.id)
