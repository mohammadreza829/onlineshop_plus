from django.urls import path

from . import views


app_name = 'shop'

"""
طراحی URLها

 ساختار :

URL	View	کاربرد
/products/	product_list	لیست محصولات
/products/<slug>/	product_detail	جزئیات محصول
/category/<slug>/	category_products	محصولات یک دسته

مثلاً:

/products/

/products/iphone-15/

/category/mobile/
"""

urlpatterns = [

    path('', views.home_view, name='home'),  # صفحه اصلی

    path(
        'products/',
        views.product_list,
        name='product_list'
    ),


    path(
        'products/<slug:slug>/',
        views.product_detail,
        name='product_detail'
    ),


    path(
        'category/<slug:slug>/',
        views.category_products,
        name='category_products'
    ),

]
