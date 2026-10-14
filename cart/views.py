from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from shop.models import Product, ProductVariant

from .cart import Cart
from .services import CartResult, parse_quantity


def selected_variant(request, product):
    value = request.POST.get("variant_id")
    if not value:
        return None
    if not value.isdigit():
        from django.http import Http404

        raise Http404
    return get_object_or_404(ProductVariant, pk=int(value), product=product)


def is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def cart_response(request, cart, result=None):
    # data = cart.summary()

    # if result:

    #     data.update({

    #         "success": result.success,

    #         "message": result.message,

    #     })

    # else:

    #     data["success"] = True
    #
    data = {"success": True, **cart.summary()}

    if result:
        data.update(
            {
                "success": result.success,
                "message": result.message,
            }
        )

    if is_ajax(request):
        return JsonResponse(data)

    if result and result.message:
        (messages.success if result.success else messages.error)(request, result.message)

    return redirect("cart:cart_detail")


# ======================================
# Cart Detail
# ======================================


def cart_detail(request):
    cart = Cart(request)
    cart.clean()
    return render(request, "cart/cart_detail.html", {"cart": cart})


# ======================================
# Add
# ======================================


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)

    product = get_object_or_404(Product, id=product_id)

    quantity = parse_quantity(request.POST.get("quantity"))
    if quantity is None:
        result = CartResult(False, "تعداد نامعتبر است.")
    else:
        result = cart.add(product, quantity, variant=selected_variant(request, product))
    return cart_response(request, cart, result)


# ======================================
# Decrease
# ======================================


@require_POST
def cart_decrease(request, product_id):
    cart = Cart(request)

    product = get_object_or_404(Product, id=product_id)

    result = cart.decrease(product, variant=selected_variant(request, product))

    return cart_response(request, cart, result)


# ======================================
# Remove
# ======================================


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)

    product = get_object_or_404(Product, id=product_id)

    result = cart.remove(product, variant=selected_variant(request, product))

    return cart_response(request, cart, result)


# ======================================
# Clear
# ======================================


@require_POST
def cart_clear(request):
    cart = Cart(request)

    cart.clear()
    #  messages.success(request,    "سبد خرید خالی شد.")
    return cart_response(request, cart)
