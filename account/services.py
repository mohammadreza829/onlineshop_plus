"""Transport-independent OTP authentication for both session login and JWT."""

from django.db import IntegrityError, transaction

from . import otp
from .models import ShopUser


def get_or_create_customer(phone):
    user = ShopUser.objects.filter(phone=phone).first()
    if user:
        return user
    try:
        with transaction.atomic():
            return ShopUser.objects.create_user(phone=phone, password=None)
    except IntegrityError:
        return ShopUser.objects.get(phone=phone)


def authenticate_otp(phone, code):
    if not otp.verify_code(phone, code):
        raise otp.OTPError("کد تایید وارد شده اشتباه است.")
    user = get_or_create_customer(phone)
    if not user.is_active:
        raise otp.OTPError("حساب کاربری شما غیرفعال است.")
    return user
