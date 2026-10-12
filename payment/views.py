from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import reverse
from django.db import transaction

from orders.models import Order
from orders.services import decrease_stock
from cart.cart import Cart
from .models import Payment
from .services import request_payment, verify_payment


@login_required
def payment_process(request, order_id):
    """
    شروع فرآیند پرداخت برای یک سفارش
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_paid:
        return HttpResponse("این سفارش قبلاً پرداخت شده است.")

    # ایجاد رکورد جدید برای پرداخت
    payment = Payment.objects.create(
        order=order,
        user=request.user,
        amount=order.total_price,
    )

    callback_url = request.build_absolute_uri(reverse("payment:verify"))
    success, payment_url = request_payment(payment, callback_url)

    if success:
        return redirect(payment_url)
    
    return HttpResponse(f"خطا در اتصال به درگاه: {payment_url}")


@login_required
def payment_verify(request):
    """
    تایید تراکنش پس از بازگشت از درگاه
    """
    authority = request.GET.get("Authority")
    status = request.GET.get("Status")

    if status != "OK" or not authority:
        return render(request, "payment/payment_failed.html", {"error": "پرداخت توسط کاربر لغو شد یا ناموفق بود."})

    payment = get_object_or_404(Payment, authority=authority, user=request.user)
    order = payment.order

    if payment.status == Payment.STATUS_SUCCESS or order.is_paid:
        return render(request, "payment/payment_success.html", {"order": order, "ref_id": payment.ref_id})

    success, ref_id = verify_payment(payment)

    if success:
        with transaction.atomic():
            # ۱. بروزرسانی وضعیت پرداخت
            payment.status = Payment.STATUS_SUCCESS
            payment.ref_id = ref_id
            payment.save(update_fields=["status", "ref_id"])

            # ۲. بروزرسانی وضعیت سفارش
            order.is_paid = True
            order.status = Order.STATUS_PAID
            order.ref_id = ref_id
            order.save(update_fields=["is_paid", "status", "ref_id"])

            # ۳. کسر موجودی انبار
            decrease_stock(order)

            # ۴. پاکسازی سبد خرید
            Cart(request).clear()

        return render(request, "payment/payment_success.html", {"order": order, "ref_id": ref_id})
    else:
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=["status"])
        return render(request, "payment/payment_failed.html", {"order": order, "error": "تراکنش توسط درگاه تایید نشد."})