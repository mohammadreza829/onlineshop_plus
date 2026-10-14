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
    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            base += ["is_staff", "is_superuser", "groups", "user_permissions"]
        return base

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(is_staff=False, is_superuser=False)

    def has_change_permission(self, request, obj=None):
        if obj and not request.user.is_superuser and (obj.is_staff or obj.is_superuser):
            return False
        return super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    ordering = ["phone"]
    add_form = ShopUserCreationForm
    form = ShopUserChangeForm
    model = ShopUser
    list_display = ("phone", "last_name", "first_name", "is_active", "is_staff")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "address")}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {"fields": ("phone", "password1", "password2")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "address")}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
