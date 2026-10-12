from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Product,
    ProductFeatures,
    ProductImage,
    Category
)


# ==========================================
# Product Image Inline
# ==========================================

class ImageInline(admin.TabularInline):

    model = ProductImage

    extra = 1

    fields = [
        'image',
        'preview',
        'description',
        'is_primary',
        'order',
    ]

    readonly_fields = [
        'preview',
    ]


    def preview(self, obj):

        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="80" style="object-fit:cover;border-radius:5px;" />',
                obj.image.url
            )

        return "بدون تصویر"


    preview.short_description = "پیش نمایش"



# ==========================================
# Product Features Inline
# ==========================================

class FeatureInline(admin.TabularInline):

    model = ProductFeatures

    extra = 1

    fields = [
        'name',
        'value',
    ]



# ==========================================
# Category Admin
# ==========================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = [
        'name',
        'parent',
        'slug',
        'created',
    ]

    list_filter = [
        'parent',
        'created',
    ]

    search_fields = [
        'name',
        'slug',
    ]

    prepopulated_fields = {
        'slug': ('name',)
    }

    readonly_fields = [
        'created',
        'updated',
    ]



# ==========================================
# Product Admin
# ==========================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = [
        'name',
        'sku',
        'category',
        'price',
        'discount_price',
        'inventory',
        'is_active',
        'created',
    ]


    list_filter = [
        'is_active',
        'category',
        'created',
    ]


    search_fields = [
        'name',
        'sku',
        'slug',
    ]


    prepopulated_fields = {
        'slug': ('name',)
    }


    readonly_fields = [
        'created',
        'updated',
        'discount_price',
    ]


    fieldsets = (

        (
            'اطلاعات اصلی محصول',
            {
                'fields': (
                    'name',
                    'slug',
                    'sku',
                    'category',
                    'description',
                )
            }
        ),


        (
            'قیمت و موجودی',
            {
                'fields': (
                    'price',
                    'off',
                    'discount_price',
                    'inventory',
                )
            }
        ),


        (
            'وضعیت',
            {
                'fields': (
                    'is_active',
                )
            }
        ),


        (
            'تاریخ‌ها',
            {
                'fields': (
                    'created',
                    'updated',
                )
            }
        ),
    )


    inlines = [
        ImageInline,
        FeatureInline,
    ]


    def discount_price(self, obj):

        return obj.final_price


    discount_price.short_description = "قیمت بعد از تخفیف"