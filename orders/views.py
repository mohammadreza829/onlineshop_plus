import logging
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from cart.common.smsir import send_sms_ir
from cart.cart import Cart

from .forms import OrderCreateForm, PhoneVerificationForm
from .models import Order
from account.models import ShopUser
from .services import (
    OrderCreationError,
    create_order_from_cart,
    get_zarinpal,
    decrease_stock,
)
from random import choices
from django.urls import reverse
from django.conf import settings
import requests
from django.http import HttpResponse
import json
from addresses.models import Address
# from zarinpal_utils.Config import Config
# from zarinpal import ZarinPal

logger = logging.getLogger(__name__)


# ======================================
# Create Order
# ======================================

# @login_required
def order_create(request):
    """
    مرحله اصلی تسویه‌حساب:
    - اگر کاربر لاگین نیست، ابتدا به لاگین پیامکی هدایت می‌شود.
    - اگر لاگین است، آدرس‌های ثبت‌شده‌اش را انتخاب یا آدرس جدید وارد می‌کند.
    """
    # ۱. بررسی ورود کاربر
    if not request.user.is_authenticated:
        messages.info(request, "لطفاً ابتدا شماره تلفن خود را تایید کنید.")
        return redirect('orders:verify_phone')

    cart = Cart(request)
    if cart.is_empty:
        messages.warning(request, "سبد خرید شما خالی است.")
        return redirect('cart:cart_detail')

    # ۲. دریافت آدرس‌های کاربر
    user_addresses = Address.objects.filter(user=request.user)

    if request.method == 'POST':
        address_id = request.POST.get('address_id')

        # بررسی انتخاب آدرس
        if not address_id:
            messages.error(
                request, "لطفاً یک آدرس برای ارسال سفارش انتخاب کنید.")
            return render(request, 'orders/create_order.html', {
                'cart': cart,
                'addresses': user_addresses
            })

        selected_address = get_object_or_404(
            Address, id=address_id, user=request.user)

        # آماده‌سازی داده‌ها برای ساخت سفارش از روی آدرس انتخاب‌شده
        cleaned_data = {
            'first_name': selected_address.receiver_name.split()[0] if selected_address.receiver_name else request.user.first_name,
            'last_name': ' '.join(selected_address.receiver_name.split()[1:]) if ' ' in selected_address.receiver_name else request.user.last_name,
            'phone': selected_address.receiver_phone,
            'address': f"{selected_address.get_province_display()} - {selected_address.city} - {selected_address.full_address}",
            'postal_code': selected_address.postal_code,
        }

        try:
            # ساخت سفارش در DB
            order = create_order_from_cart(cart, cleaned_data, request.user)
            # لینک کردن رکورد آدرس به سفارش
            order.address_obj = selected_address
            order.save(update_fields=['address_obj'])

            # هدایت مستقیم به درگاه پرداخت
            return redirect('payment:process', order_id=order.id)

        except OrderCreationError as e:
            messages.error(request, str(e))
            return redirect('cart:cart_detail')

    return render(request, 'orders/create_order.html', {
        'cart': cart,
        'addresses': user_addresses
    })

# ======================================
# Order Detail
# ======================================


@login_required
def order_detail(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
    )

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
        },
    )


# ======================================
# Order List
# ======================================

@login_required
def order_list(request):

    orders = (
        request.user.orders
        .all()
        .prefetch_related("items")
        .order_by("-created")
    )

    return render(
        request,
        "orders/order_list.html",
        {
            "orders": orders,
        },
    )


logger = logging.getLogger(__name__)


def verify_phone(request):
    # اگر کاربر قبلاً وارد شده، نیازی به OTP نیست
    if request.user.is_authenticated:
        return redirect('orders:order_create')

    if request.method == 'POST':
        form = PhoneVerificationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data.get('phone')
            otp = ''.join(choices('0123456789', k=6))
            request.session["verification_code"] = otp
            request.session["phone"] = phone
            print(f"OTP for {phone}: {otp}")  # برای تست در کنسول چاپ می‌کنیم
            # send_sms_ir(otp, phone)
            messages.info(request, 'کد تایید برای شما ارسال شد.')
            return redirect('orders:verify_code')
    else:
        form = PhoneVerificationForm()

    return render(request, 'orders/verify_phone.html', {'form': form})


def verify_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        verification_code = request.session.get('verification_code')
        phone = request.session.get('phone')

        if code and verification_code and code == verification_code:
            # اگر کاربر وجود داشت، لاگین می‌شود؛ در غیر این صورت ساخته می‌شود
            user, created = ShopUser.objects.get_or_create(
                phone=phone,
                defaults={'first_name': '', 'last_name': ''}
            )

            login(request, user)

            # پاکسازی جلسات تایید
            request.session.pop('verification_code', None)
            request.session.pop('phone', None)

            return redirect('orders:order_create')
        else:
            messages.error(request, 'کد تایید وارد شده اشتباه است.')

    return render(request, 'orders/verify_code.html')


# Endpoints
SANDBOX = 'sandbox' if getattr(settings, 'SANDBOX', False) else 'www'
ZP_API_REQUEST = f"https://{SANDBOX}.zarinpal.com/pg/rest/WebGate/PaymentRequest.json"
ZP_API_STARTPAY = f"https://{SANDBOX}.zarinpal.com/pg/StartPay/"


# @login_required
# def payment_request(request, order_id):

#     order = get_object_or_404(
#         Order,
#         id=order_id,
#         user=request.user
#     )

#     if order.is_paid:

#         return HttpResponse(
#             "این سفارش قبلاً پرداخت شده است."
#         )

#     zp = get_zarinpal()

#     payment_data = {

#         "amount": int(order.total_price),

#         "description": (
#             f"Payment for order {order.order_number}"
#         ),

#         "callback_url": request.build_absolute_uri(
#             reverse(
#                 "orders:payment_verify"
#             )
#         ),

#     }

#     result = zp.payments.create(
#         payment_data
#     )

#     if result["data"]["code"] == 100:

#         authority = result["data"]["authority"]

#         order.authority = authority

#         order.save(
#             update_fields=[
#                 "authority"
#             ]
#         )

#         payment_url = (
#             zp.payments.generate_payment_url(
#                 authority
#             )
#         )

#         return redirect(
#             payment_url
#         )

#     return HttpResponse(
#         result
#     )


# @login_required
# def payment_verify(request):

#     authority = request.GET.get(
#         "Authority"
#     )

#     status = request.GET.get(
#         "Status"
#     )

#     if status != "OK":

#         return HttpResponse(
#             "پرداخت لغو شد."
#         )

#     order = get_object_or_404(

#         Order,

#         authority=authority,

#         user=request.user

#     )

#     if order.is_paid:
#         return render(
#             request,
#             "orders/payment_success.html",
#             {
#                 "order": order
#             }
#         )

#     zp = get_zarinpal()

#     verify_data = {

#         "amount": int(order.total_price),

#         "authority": authority,

#     }

#     result = zp.verifications.verify(
#         verify_data
#     )

#     if result["data"]["code"] == 100:

#         order.is_paid = True

#         order.status = Order.STATUS_PAID

#         order.ref_id = (
#             result["data"]["ref_id"]
#         )

#         order.save(
#             update_fields=[
#                 "is_paid",
#                 "status",
#                 "ref_id",
#             ]
#         )

#         decrease_stock(order)

#         cart = Cart(request)

#         cart.clear()

#         return render(

#             request,

#             "orders/payment_success.html",

#             {
#                 "order": order
#             }

#         )

#     return render(

#         request,

#         "orders/payment_failed.html",

#         {
#             "order": order
#         }

#     )

# def send_request(request):
#     # ۱. دریافت ایمن سفارش از Session
#     order_id = request.session.get('order_id')
#     if not order_id:
#         return HttpResponse('سفارشی یافت نشد.', status=404)

#     order = get_object_or_404(Order, id=order_id)

#     # ۲. ساخت دینامیک CallbackURL (به جای هاردکد کردن IP local)
#     callback_url = request.build_absolute_uri(
#         reverse('orders:verify'))  # نام route خود را جایگزین کنید

#     description = ", ".join([item.product.name for item in order.items.all()])

#     # ۳. تبدیل Decimal به int برای جلوگیری از خطای Serialization
#     data = {
#         "MerchantID": settings.MERCHANT,
#         "Amount": int(order.total_price),  # <--- اصل اصلاحیه اینجاست
#         "Description": description,
#         "Phone": getattr(request.user, 'phone', ''),
#         "CallbackURL": callback_url,
#     }

#     headers = {
#         'accept': 'application/json',
#         'content-type': 'application/json',
#     }

#     try:
#         # استفاده از پارامتر json= به جای data=json.dumps(...) که نیازی به محاسبه content-length دستی ندارد
#         response = requests.post(
#             ZP_API_REQUEST, json=data, headers=headers, timeout=10)
#         print('#'*80)
#         print(f'status code: {response.status_code}')
#         if response.status_code == 200:
#             response_json = response.json()
#             if response_json.get('Status') == 100:
#                 authority = response_json['Authority']
#                 return redirect(ZP_API_STARTPAY + authority)
#             else:
#                 return HttpResponse(f"خطا از سمت زرین‌پال: کد {response_json.get('Status')}")

#         return HttpResponse('پاسخی از درگاه دریافت نشد.')

#     except requests.exceptions.Timeout:
#         return HttpResponse('خطای تایم‌آوت در ارتباط با درگاه.')
#     except requests.exceptions.ConnectionError:
#         return HttpResponse('خطای در ارتباط با شبکه.')

# def verify(request):
#     # ۱. چک کردن انصراف یا لغو توسط کاربر
#     authority = request.GET.get('Authority')
#     status = request.GET.get('Status')

#     if status != 'OK' or not authority:
#         return render(request, 'payment-tracking.html', {
#             "success": False,
#             "error_message": "پرداخت توسط کاربر لغو شد یا ناموفق بود."
#         })

#     # ۲. دریافت ایمن order_id از Session
#     order_id = request.session.get('order_id')
#     if not order_id:
#         return render(request, 'payment-tracking.html', {
#             "success": False,
#             "error_message": "سفارشی یافت نشد یا جلسه کاری شما منقضی شده است."
#         })

#     order = get_object_or_404(Order, id=order_id)

#     # ۳. ارسال درخواست تایید به زرین‌پال
#     data = {
#         "MerchantID": settings.MERCHANT,
#         "Amount": int(order.total_price),  # تبدیل به int برای جلوگیری از خطای Decimal
#         "Authority": authority,
#     }

#     headers = {
#         'accept': 'application/json',
#         'content-type': 'application/json',
#     }

#     try:
#         response = requests.post(ZP_API_VERIFY, json=data, headers=headers, timeout=10)

#         if response.status_code == 200:
#             response_json = response.json()
#             response_status = response_json.get('Status')

#             # وضعیت ۱۰۰ (پرداخت موفق) یا ۱۰۱ (پرداخت قبلاً تایید شده)
#             if response_status in [100, 101]:
#                 ref_id = response_json.get('RefID')

#                 # ۴. به‌روزرسانی دیتابیس در یک Atomic Transaction برای امنیت داده‌ها
#                 with transaction.atomic():
#                     # کاهش موجودی انبار
#                     for item in order.items.select_related('product').all():
#                         item.product.inventory -= item.quantity
#                         item.product.save()

#                     # ثبت پرداخت موفق سفارش
#                     order.paid = True
#                     # بهتر است کد پیگیری را هم در سفارش ذخیره کنید:
#                     # order.zarinpal_ref_id = ref_id
#                     order.save()

#                 # ۵. پاک کردن سفارش از session پس از موفقیت
#                 if 'order_id' in request.session:
#                     del request.session['order_id']

#                 return render(request, 'payment-tracking.html', {
#                     "success": True,
#                     "RefID": ref_id,
#                     "order_id": order.id
#                 })
#             else:
#                 return render(request, 'payment-tracking.html', {
#                     "success": False,
#                     "error_message": f"خطا در تایید تراکنش. کد خطا: {response_status}"
#                 })

#         return render(request, 'payment-tracking.html', {
#             "success": False,
#             "error_message": "پاسخ معتبری از درگاه دریافت نشد."
#         })

#     except requests.exceptions.Timeout:
#         return HttpResponse('خطای تایم‌آوت در ارتباط با درگاه.')
#     except requests.exceptions.ConnectionError:
#         return HttpResponse('خطای در ارتباط با شبکه.')

# def order_payment(request, payment_amount):
#     config = Config(
#         access_token="YourAccessToken",
#         merchant_id="YourMerchantId",
#         sandbox=True,  # Use sandbox environment
#     )

#     zarinpal = ZarinPal(config)
#     try:
#         config = Config(
#             access_token="YourAccessToken",
#         )
#         zarinpal = ZarinPal(config)

#         transactions = zarinpal.transactions.list({
#             "terminal_id": "YourTerminalID",
#             "filter": "PAID",
#             "limit": 10,
#             "offset": 0,
#         })

#         print("Transactions List:", transactions)
#     except Exception as e:
#         print("Error fetching transactions:", e)
