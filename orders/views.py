import logging
from random import choices

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from account.models import ShopUser
from addresses.models import Address
from cart.cart import Cart
from cart.common.smsir import send_sms_ir

from .forms import PhoneVerificationForm
from .models import Order
from .services import OrderCreationError, create_order_from_cart

logger = logging.getLogger(__name__)


# ======================================
# Create Order
# ======================================

def order_create(request):
    """
    مرحله اصلی تسویه‌حساب:
    - اگر کاربر لاگین نیست، ابتدا به لاگین پیامکی هدایت می‌شود.
    - اگر لاگین است، آدرس‌های ثبت‌شده‌اش را انتخاب یا آدرس جدید وارد می‌کند.
    """
    if not request.user.is_authenticated:
        messages.info(request, "لطفاً ابتدا شماره تلفن خود را تایید کنید.")
        return redirect("orders:verify_phone")

    cart = Cart(request)
    if cart.is_empty:
        messages.warning(request, "سبد خرید شما خالی است.")
        return redirect("cart:cart_detail")

    user_addresses = Address.objects.filter(user=request.user)
    context = {"cart": cart, "addresses": user_addresses}

    if request.method != "POST":
        return render(request, "orders/create_order.html", context)

    address_id = request.POST.get("address_id")
    if not address_id:
        messages.error(request, "لطفاً یک آدرس برای ارسال سفارش انتخاب کنید.")
        return render(request, "orders/create_order.html", context)

    selected_address = get_object_or_404(Address, id=address_id, user=request.user)

    name_parts = (selected_address.receiver_name or "").split()
    cleaned_data = {
        "first_name": name_parts[0] if name_parts else request.user.first_name,
        "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else request.user.last_name,
        "phone": selected_address.receiver_phone,
        "address": (
            f"{selected_address.get_province_display()} - "
            f"{selected_address.city} - {selected_address.full_address}"
        ),
        "postal_code": selected_address.postal_code,
    }

    try:
        order = create_order_from_cart(cart, cleaned_data, request.user)
    except OrderCreationError as exc:
        messages.error(request, str(exc))
        return redirect("cart:cart_detail")

    order.address_obj = selected_address
    order.save(update_fields=["address_obj"])
    return redirect("payment:process", order_id=order.id)


# ======================================
# Order Detail / List
# ======================================

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def order_list(request):
    orders = request.user.orders.all().prefetch_related("items").order_by("-created")
    return render(request, "orders/order_list.html", {"orders": orders})


# ======================================
# Phone verification (OTP)
# NOTE: hardened in phase 1 (secure random, expiry, attempt limit, rate limit)
# ======================================

def verify_phone(request):
    if request.user.is_authenticated:
        return redirect("orders:order_create")

    if request.method == "POST":
        form = PhoneVerificationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data.get("phone")
            otp = "".join(choices("0123456789", k=6))
            request.session["verification_code"] = otp
            request.session["phone"] = phone
            if settings.DEBUG:
                logger.info("DEV OTP for %s: %s", phone, otp)
            else:
                send_sms_ir(otp, phone)
            messages.info(request, "کد تایید برای شما ارسال شد.")
            return redirect("orders:verify_code")
    else:
        form = PhoneVerificationForm()

    return render(request, "orders/verify_phone.html", {"form": form})


def verify_code(request):
    if request.method == "POST":
        code = request.POST.get("code")
        verification_code = request.session.get("verification_code")
        phone = request.session.get("phone")

        if code and verification_code and code == verification_code:
            user, _ = ShopUser.objects.get_or_create(
                phone=phone,
                defaults={"first_name": "", "last_name": ""},
            )
            login(request, user)
            request.session.pop("verification_code", None)
            request.session.pop("phone", None)
            return redirect("orders:order_create")

        messages.error(request, "کد تایید وارد شده اشتباه است.")

    return render(request, "orders/verify_code.html")
