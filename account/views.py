from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages

from orders.models import Order
from .forms import UserProfileForm


@login_required
def profile_view(request):
    """
    مشاهده و ویرایش اطلاعات پروفایل کاربر + نمایش سفارشات قبلی با قابلیت فیلتر
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "اطلاعات پروفایل با موفقیت بروزرسانی شد.")
            return redirect('account:profile')
        else:
            messages.error(request, "لطفاً خطاهای فرم را برطرف کنید.")
    else:
        form = UserProfileForm(instance=request.user)

    # دریافت تمامی سفارش‌های همین کاربر همراه با آیتم‌های آن
    orders = Order.objects.filter(user=request.user).prefetch_related('items')

    # اعمال فیلتر بر اساس وضعیت سفارش (در صورت ارسال در Query String)
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    return render(
        request,
        'account/profile.html',
        {
            'form': form,
            'orders': orders,
            'selected_status': status_filter or '',
            'status_choices': Order.STATUS_CHOICES,
        }
    )
    
@login_required
def logout_view(request):
    """
    خروج کاربر از حساب کاربری
    """
    logout(request)
    messages.info(request, "شما از حساب کاربری خود خارج شدید.")
    return redirect('shop:product_list')