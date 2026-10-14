from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Category
from .selectors import catalog_detail, catalog_products

# ==========================================
# Product List
# ==========================================


def product_list(request):
    query = request.GET.get("q")
    ordering = {"price_low": "price", "price_high": "-price", "oldest": "created"}.get(
        request.GET.get("sort"), "-created"
    )
    products = catalog_products(
        search=query, category=request.GET.get("category"), stock=request.GET.get("stock"), ordering=ordering
    )

    paginator = Paginator(products, 12)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    # ==========================
    # Categories
    # ==========================

    categories = Category.objects.filter(parent=None)

    context = {
        "products": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "query": query,
    }

    # request.session['phone'] = '09171070235'
    return render(request, "shop/product_list.html", context)


# ==========================================
# Product Detail
# ==========================================


def product_detail(request, slug):
    product = get_object_or_404(catalog_detail(), slug=slug)
    phone = request.session.get("phone")
    context = {"product": product, "phone": phone}

    return render(request, "shop/product_detail.html", context)


# ==========================================
# Category Products
# ==========================================


def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)

    products = catalog_products(category=category.slug)

    context = {"category": category, "products": products}

    return render(request, "shop/category_products.html", context)


def home_view(request):
    """
    نمایش صفحه اصلی فروشگاه (اصلی / Index)
    """
    categories = Category.objects.all()[:6]  # دریافت ۶ دسته‌بندی اول
    latest_products = catalog_products()[:8]  # جدیدترین محصولات

    return render(
        request,
        "shop/index.html",
        {
            "categories": categories,
            "latest_products": latest_products,
        },
    )
