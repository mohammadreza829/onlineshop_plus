from django.shortcuts import render, get_object_or_404

from .models import Product, Category
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q


# ==========================================
# Product List
# ==========================================

def product_list(request):

    products = Product.objects.filter(
        is_active=True
    ).select_related(
        'category'
    )

    # ==========================
    # Search
    # ==========================

    query = request.GET.get('q')

    if query:

        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query)
        )

    # ==========================
    # Category Filter
    # ==========================

    category_slug = request.GET.get('category')

    if category_slug:

        products = products.filter(
            category__slug=category_slug
        )

    # ==========================
    # Stock Filter
    # ==========================

    stock = request.GET.get('stock')

    if stock == 'available':

        products = products.filter(
            inventory__gt=0
        )

    elif stock == 'out':

        products = products.filter(
            inventory=0
        )

    # ==========================
    # Sorting
    # ==========================

    sort = request.GET.get('sort')

    if sort == 'price_low':

        products = products.order_by(
            'price'
        )

    elif sort == 'price_high':

        products = products.order_by(
            '-price'
        )

    elif sort == 'oldest':

        products = products.order_by(
            'created'
        )

    else:

        products = products.order_by(
            '-created'
        )

    # ==========================
    # Pagination
    # ==========================

    paginator = Paginator(
        products,
        12
    )

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(
        page_number
    )

    # ==========================
    # Categories
    # ==========================

    categories = Category.objects.filter(
        parent=None
    )

    context = {

        'products': page_obj,

        'page_obj': page_obj,

        'categories': categories,

        'query': query,

    }

    # request.session['phone'] = '09171070235'
    return render(
        request,
        'shop/product_list.html',
        context
    )

# ==========================================
# Product Detail
# ==========================================


def product_detail(request, slug):

    product = get_object_or_404(
        Product,
        slug=slug,
        is_active=True
    )
    phone = request.session.get('phone')
    context = {
        'product': product,
        'phone': phone
    }

    return render(
        request,
        'shop/product_detail.html',
        context
    )


# ==========================================
# Category Products
# ==========================================

def category_products(request, slug):

    category = get_object_or_404(
        Category,
        slug=slug
    )

    products = Product.objects.filter(
        category=category,
        is_active=True
    )

    context = {
        'category': category,
        'products': products
    }

    return render(
        request,
        'shop/category_products.html',
        context
    )


def home_view(request):
    """
    نمایش صفحه اصلی فروشگاه (اصلی / Index)
    """
    categories = Category.objects.all()[:6]  # دریافت ۶ دسته‌بندی اول
    latest_products = Product.objects.filter(is_active=True).order_by(
        '-created')[:8]  # جدیدترین محصولات

    return render(request, 'shop/index.html', {
        'categories': categories,
        'latest_products': latest_products,
    })
