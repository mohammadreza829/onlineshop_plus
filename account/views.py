import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from orders.models import Order

from . import otp
from .forms import OTPCodeForm, PhoneLoginForm, UserProfileForm
from .models import ShopUser

logger = logging.getLogger(__name__)

SESSION_PHONE = "otp_phone"
SESSION_NEXT = "otp_next"


def _safe_next(request, value):
    if value and url_has_allowed_host_and_scheme(
        value, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return value
    return ""


def _get_or_create_user(phone):
    user = ShopUser.objects.filter(phone=phone).first()
    if user:
        return user
    try:
        with transaction.atomic():
            # password=None -> unusable password: OTP is the only way in.
            return ShopUser.objects.create_user(phone=phone, password=None)
    except IntegrityError:  # two parallel verifications for a brand-new number
        return ShopUser.objects.get(phone=phone)


def login_view(request):
    """Step 1: ask for the mobile number and send a code."""
    next_url = _safe_next(request, request.POST.get("next") or request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(next_url or "shop:home")

    form = PhoneLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        try:
            otp.send_code(phone, ip=request.META.get("REMOTE_ADDR"))
        except otp.OTPError as exc:
            # Still move to step 2 if a valid code was already sent (cooldown case).
            messages.error(request, str(exc))
            if not exc.retry_after or request.session.get(SESSION_PHONE) != phone:
                return render(request, "account/login.html", {"form": form, "next": next_url})
        else:
            messages.success(request, "کد تایید برای شما پیامک شد.")
        request.session[SESSION_PHONE] = phone
        request.session[SESSION_NEXT] = next_url
        return redirect("account:verify_code")

    return render(request, "account/login.html", {"form": form, "next": next_url})


def verify_code_view(request):
    """Step 2: check the code, log in (and register on first login)."""
    phone = request.session.get(SESSION_PHONE)
    if not phone:
        return redirect("account:login")

    form = OTPCodeForm(request.POST or None)
    if request.method == "POST" and request.POST.get("action") == "resend":
        try:
            otp.send_code(phone, ip=request.META.get("REMOTE_ADDR"))
            messages.success(request, "کد جدید ارسال شد.")
        except otp.OTPError as exc:
            messages.error(request, str(exc))
        return redirect("account:verify_code")

    if request.method == "POST" and form.is_valid():
        try:
            ok = otp.verify_code(phone, form.cleaned_data["code"])
        except otp.OTPError as exc:
            messages.error(request, str(exc))
            ok = False
        else:
            if not ok:
                messages.error(request, "کد تایید وارد شده اشتباه است.")

        if ok:
            user = _get_or_create_user(phone)
            if not user.is_active:
                messages.error(request, "حساب کاربری شما غیرفعال است.")
                return redirect("account:login")
            next_url = request.session.get(SESSION_NEXT) or ""
            # login() rotates the session key (session fixation) but keeps the cart.
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            request.session.pop(SESSION_PHONE, None)
            request.session.pop(SESSION_NEXT, None)
            return redirect(_safe_next(request, next_url) or "shop:home")

    masked = f"{phone[:4]}***{phone[-4:]}"
    return render(
        request,
        "account/verify_code.html",
        {"form": form, "masked_phone": masked, "cooldown": otp.cooldown_remaining(phone)},
    )


@login_required
def profile_view(request):
    """
    مشاهده و ویرایش اطلاعات پروفایل کاربر + نمایش سفارشات قبلی با قابلیت فیلتر
    """
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "اطلاعات پروفایل با موفقیت بروزرسانی شد.")
            return redirect("account:profile")
        messages.error(request, "لطفاً خطاهای فرم را برطرف کنید.")
    else:
        form = UserProfileForm(instance=request.user)

    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    status_filter = request.GET.get("status")
    if status_filter:
        orders = orders.filter(status=status_filter)

    return render(
        request,
        "account/profile.html",
        {
            "form": form,
            "orders": orders,
            "selected_status": status_filter or "",
            "status_choices": Order.STATUS_CHOICES,
        },
    )


@require_POST
def logout_view(request):
    """POST only: a GET logout can be triggered by any <img> tag on another site."""
    logout(request)
    messages.info(request, "شما از حساب کاربری خود خارج شدید.")
    return redirect("shop:product_list")
