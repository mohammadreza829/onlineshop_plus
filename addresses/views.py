from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AddressForm
from .selectors import addresses_for_user
from .services import save_address


@login_required
def address_list(request):
    """لیست آدرس‌های کاربر"""
    addresses = addresses_for_user(request.user)
    return render(request, "addresses/address_list.html", {"addresses": addresses})


@login_required
def address_create(request):
    """افزودن آدرس جدید"""
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            save_address(user=request.user, data=form.cleaned_data)
            messages.success(request, "آدرس جدید با موفقیت اضافه شد.")
            return redirect("addresses:address_list")
    else:
        form = AddressForm()

    return render(request, "addresses/address_form.html", {"form": form, "title": "افزودن آدرس"})


@login_required
def address_edit(request, pk):
    """ویرایش آدرس"""
    address = get_object_or_404(addresses_for_user(request.user), pk=pk)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            save_address(user=request.user, data=form.cleaned_data, address=address)
            messages.success(request, "آدرس بروزرسانی شد.")
            return redirect("addresses:address_list")
    else:
        form = AddressForm(instance=address)

    return render(request, "addresses/address_form.html", {"form": form, "title": "ویرایش آدرس"})


@login_required
def address_delete(request, pk):
    """حذف آدرس"""
    address = get_object_or_404(addresses_for_user(request.user), pk=pk)
    if request.method == "POST":
        address.delete()
        messages.success(request, "آدرس حذف شد.")
        return redirect("addresses:address_list")
    return render(request, "addresses/address_confirm_delete.html", {"address": address})


@login_required
@require_POST
def set_default_address(request, pk):
    """تنظیم به عنوان آدرس پیش‌فرض"""
    address = get_object_or_404(addresses_for_user(request.user), pk=pk)
    save_address(user=request.user, data={"is_default": True}, address=address)
    messages.success(request, f"آدرس «{address.title}» به عنوان پیش‌فرض انتخاب شد.")
    return redirect("addresses:address_list")
