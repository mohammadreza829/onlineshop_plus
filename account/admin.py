# from django.contrib import admin
# from .models import *
# from django.contrib.auth.admin import UserAdmin
# from .forms import ShopUserChangeForm, ShopUserCreationForm


# # Register your models here.

# @admin.register(ShopUser)
# class UserAdmin(UserAdmin):
#     ordering = ['phone']
#     add_form = ShopUserCreationForm
#     form = ShopUserChangeForm
#     model = ShopUser
#     list_display = ('phone', 'last_name', 'first_name', 'is_active', 'is_staff')

#     fieldsets = (
#         (None, {'fields': ('phone', 'password')}),
#         ('Personal info', {'fields': ('first_name', 'last_name', 'address')}),
#         ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
#         ('dates', {'fields': ('last_login', 'date_joined')}),
#     )

#     add_fieldsets = (
#         (None, {'fields': ('phone', 'password1', 'password2')}),
#         ('Personal info', {'fields': ('first_name', 'last_name', 'address')}),
#         ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
#         ('dates', {'fields': ('last_login', 'date_joined')}),
#     )
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import ShopUserChangeForm, ShopUserCreationForm
from .models import ShopUser


@admin.register(ShopUser)
class CustomUserAdmin(UserAdmin):
    ordering = ['phone']
    add_form = ShopUserCreationForm
    form = ShopUserChangeForm
    model = ShopUser
    list_display = ('phone', 'last_name', 'first_name',
                    'is_active', 'is_staff')

    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'address')}),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
        ('تاریخ‌ها', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {'fields': ('phone', 'password1', 'password2')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'address')}),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
    )
