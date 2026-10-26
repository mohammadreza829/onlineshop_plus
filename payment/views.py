from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from cart.cart import Cart
from orders.models import Order

from .models import Payment
from .services import PaymentError, process_callback, start_payment


def redirect_to_gateway(request, order):
    """Shared by checkout and the "pay again" button. Returns an HttpResponse."""
    callback_url = request.build_absolute_uri(reverse("payment:verify"))
    try:
        payment_url = start_payment(order, request.user, callback_url)
    except PaymentError as exc:
        messages.error(request, str(exc))
        return redirect("orders:order_detail", order_id=order.id)
    return redirect(payment_url)


@login_required
@require_POST
def payment_process(request, order_id):
    """Retry payment for an existing (still reserved) order."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return redirect_to_gateway(request, order)


def storefront_result(order_id=None):
    destination = f"{settings.FRONTEND_ORIGIN}/payment/result"
    if order_id is not None:
        destination += f"?order={order_id}"
    response = redirect(destination)
    response.status_code = 303
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


def payment_verify(request, storefront=False):
    """
    Gateway callback. Deliberately NOT login_required: if the session was lost on
    the way back we must still verify (the money may have been taken). The
    authority is an unguessable gateway token; order details are only shown to
    the owner.
    """
    authority = request.GET.get("Authority", "").strip()
    if not authority:
        if storefront and settings.FRONTEND_ORIGIN:
            return storefront_result()
        return render(
            request, "payment/payment_failed.html", {"error": "اطلاعات بازگشت از درگاه ناقص است."}, status=400
        )

    try:
        outcome = process_callback(authority)
    except Payment.DoesNotExist:
        if storefront and settings.FRONTEND_ORIGIN:
            return storefront_result()
        return render(request, "payment/payment_failed.html", {"error": "تراکنش یافت نشد."}, status=404)

    is_owner = request.user.is_authenticated and outcome.payment.user_id == request.user.id
    context = {"order": outcome.order if is_owner else None, "payment": outcome.payment}

    if storefront and settings.FRONTEND_ORIGIN:
        # Verification has completed server-side, even without a Django session.
        # Never trust Status, next, return_to or any browser-supplied origin.
        # No order details, tokens, authority or claimed success in this URL;
        # the frontend must authenticate and fetch the owner-scoped order API.
        # Do NOT clear the session cart: it may contain newer selections.
        return storefront_result(outcome.order.pk)

    if outcome.succeeded:
        if is_owner:
            Cart(request).clear()
        context["ref_id"] = outcome.payment.ref_id
        context["needs_review"] = outcome.order.status == Order.STATUS_NEEDS_REVIEW
        return render(request, "payment/payment_success.html", context)

    if outcome.status == Payment.STATUS_UNKNOWN:
        return render(request, "payment/payment_pending.html", context)

    context["error"] = (
        "پرداخت انجام نشد یا توسط شما لغو شد. در صورت کسر وجه، مبلغ ظرف ۷۲ ساعت توسط بانک بازگردانده می‌شود."
    )
    return render(request, "payment/payment_failed.html", context)
