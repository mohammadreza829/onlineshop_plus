from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.http import JsonResponse

from django.views.decorators.http import require_POST

from shop.models import Product

from .cart import Cart
from sms_ir import SmsIr
from django.conf import settings
from .common import smsir

def is_ajax(request):

    return (
        request.headers.get(
            "X-Requested-With"
        )
        ==
        "XMLHttpRequest"
    )


def cart_response(
    request,
    cart,
    result=None
):

    # data = cart.summary()

    # if result:

    #     data.update({

    #         "success": result.success,

    #         "message": result.message,

    #     })

    # else:

    #     data["success"] = True
    #
    data = {
        "success": True,
        **cart.summary()
    }

    if result:

        data.update(
            {
                "success": result.success,
                "message": result.message,
            }
        )

    if is_ajax(request):

        return JsonResponse(
            data
        )

    return redirect(
        "cart:cart_detail"
    )


# ======================================
# Cart Detail
# ======================================

def cart_detail(request):
    # api_key = 'XsfH1Zx3b9XVXTfNB0sqi3pasTdTBNLIKQHxU1fx8VdwjZG2'
    # linenumber = '50003181890144'
    sms_ir = SmsIr(settings.SMS_IR_API_KEY, settings.SMS_IR_LINE_NUMBER)
    # sms_ir.send_sms('09171070235', 'سلام', linenumber,)
    cart = Cart(request)
    cart.clean()
    return render(
        request,
        "cart/cart_detail.html",
        {
            "cart": cart
        }
    )


# ======================================
# Add
# ======================================

@require_POST
def cart_add(
    request,
    product_id
):

    cart = Cart(request)

    product = get_object_or_404(
        Product,
        id=product_id
    )
    
    quantity = int(
        request.POST.get(
            "quantity",
            1
        )
    )
    
    result = cart.add(
        product,
        quantity
    )
    print(10)
    # smsir.send_sms_ir(f'مشتری گرامی محصول {product} به سبد شما اضافه شد','09173838328')
    print(11)
    return cart_response(
        request,
        cart,
        result
    )


# ======================================
# Decrease
# ======================================

@require_POST
def cart_decrease(
    request,
    product_id
):

    cart = Cart(request)

    product = get_object_or_404(
        Product,
        id=product_id
    )

    result = cart.decrease(
        product
    )

    return cart_response(
        request,
        cart,
        result
    )


# ======================================
# Remove
# ======================================

@require_POST
def cart_remove(
    request,
    product_id
):

    cart = Cart(request)

    product = get_object_or_404(
        Product,
        id=product_id
    )

    result = cart.remove(
        product
    )

    return cart_response(
        request,
        cart,
        result
    )


# ======================================
# Clear
# ======================================

@require_POST
def cart_clear(request):

    cart = Cart(request)

    cart.clear()
    #  messages.success(request,    "سبد خرید خالی شد.")
    return cart_response(
        request,
        cart
    )
