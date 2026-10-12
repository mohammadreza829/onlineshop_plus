from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Address
from .forms import AddressForm


@login_required
def address_list(request):
    """لیست آدرس‌های کاربر"""
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'addresses/address_list.html', {'addresses': addresses})


@login_required
def address_create(request):
    """افزودن آدرس جدید"""
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            # اگر این اولین آدرس کاربر است، خودکار پیش‌فرض شود
            if not Address.objects.filter(user=request.user).exists():
                address.is_default = True
            address.save()
            messages.success(request, "آدرس جدید با موفقیت اضافه شد.")
            return redirect('addresses:address_list')
    else:
        form = AddressForm()

    return render(request, 'addresses/address_form.html', {'form': form, 'title': 'افزودن آدرس'})


@login_required
def address_edit(request, pk):
    """ویرایش آدرس"""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "آدرس بروزرسانی شد.")
            return redirect('addresses:address_list')
    else:
        form = AddressForm(instance=address)

    return render(request, 'addresses/address_form.html', {'form': form, 'title': 'ویرایش آدرس'})


@login_required
def address_delete(request, pk):
    """حذف آدرس"""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, "آدرس حذف شد.")
        return redirect('addresses:address_list')
    return render(request, 'addresses/address_confirm_delete.html', {'address': address})


@login_required
def set_default_address(request, pk):
    """تنظیم به عنوان آدرس پیش‌فرض"""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, f"آدرس «{address.title}» به عنوان پیش‌فرض انتخاب شد.")
    return redirect('addresses:address_list')