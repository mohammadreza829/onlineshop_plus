from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# ==========================================
# Category
# ==========================================


class Category(models.Model):
    name = models.CharField(max_length=50, verbose_name="دسته بندی محصولات")

    slug = models.SlugField(max_length=250, unique=True, db_index=True)

    parent = models.ForeignKey(
        "self",
        related_name="children",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="دسته والد",
    )

    created = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    updated = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        ordering = ["name"]

        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["parent"]),
        ]

        verbose_name = "دسته بندی"
        verbose_name_plural = "دسته بندی ها"

    def __str__(self):
        return self.name


# ==========================================
# Product
# ==========================================


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="دسته بندی",
    )

    sku = models.CharField(max_length=50, unique=True, verbose_name="کد محصول")

    name = models.CharField(max_length=250, verbose_name="نام محصول")

    slug = models.SlugField(max_length=250, unique=True, db_index=True)

    description = models.TextField(blank=True, verbose_name="توضیحات")

    inventory = models.PositiveIntegerField(default=0, verbose_name="موجودی")

    price = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="قیمت")

    off = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="درصد تخفیف"
    )

    is_active = models.BooleanField(default=True, verbose_name="فعال")

    created = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    updated = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    weight = models.DecimalField(default=1, max_digits=100, decimal_places=0, verbose_name="وزن")

    class Meta:
        ordering = ["-created"]

        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_active"]),
        ]

        verbose_name = "محصول"
        verbose_name_plural = "محصولات"

    def __str__(self):
        return self.name

    @property
    def available_stock(self):
        if hasattr(self, "stock_available"):
            return self.stock_available
        variants = list(self.variants.all())
        return sum(v.inventory for v in variants if v.is_active) if variants else self.inventory

    @property
    def final_price(self):
        """Price after discount, rounded to a whole Toman (prices have no decimals)."""
        if self.off >= 100:
            return Decimal("0")
        discounted = Decimal(self.price) * (Decimal(100) - Decimal(self.off)) / Decimal(100)
        return discounted.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


# ==========================================
# Product Features
# ==========================================


class ProductFeatures(models.Model):
    product = models.ForeignKey(
        Product, related_name="features", on_delete=models.CASCADE, verbose_name="محصول"
    )

    name = models.CharField(max_length=250, verbose_name="مشخصات")

    value = models.CharField(max_length=250, verbose_name="مقدار ویژگی")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "name", "value"], name="unique_product_feature")
        ]

        verbose_name = "ویژگی محصول"
        verbose_name_plural = "ویژگی های محصول"

    def __str__(self):
        return f"{self.name}: {self.value}"


# ==========================================
# Product Images
# ==========================================


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE, verbose_name="محصول"
    )

    image = models.ImageField(upload_to="products/", verbose_name="تصویر")

    description = models.CharField(max_length=250, blank=True, verbose_name="توضیحات تصویر")

    is_primary = models.BooleanField(default=False, verbose_name="تصویر اصلی")

    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        ordering = ["order"]

        constraints = [
            models.UniqueConstraint(
                fields=["product"], condition=models.Q(is_primary=True), name="unique_primary_product_image"
            )
        ]

        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"

    def __str__(self):
        return self.description or f"Image #{self.id}"


class ProductVariant(models.Model):
    """Variants own stock and price; base stock is not sellable when variants exist."""

    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    sku = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=60, blank=True)
    size = models.CharField(max_length=60, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(0)])
    inventory = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["product", "color", "size"], name="unique_variant_options"),
            models.CheckConstraint(condition=models.Q(price__gte=0), name="variant_nonnegative_price"),
        ]

    def __str__(self):
        return f"{self.sku}: {self.color} {self.size}"

    @property
    def final_price(self):
        if self.product.off >= 100:
            return Decimal("0")
        return (self.price * (Decimal(100) - self.product.off) / 100).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )


class Favorite(models.Model):
    user = models.ForeignKey("account.ShopUser", on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorites")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_favorite")]

    def __str__(self):
        return f"{self.user_id}/{self.product_id}"


class Review(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    user = models.ForeignKey("account.ShopUser", on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=10,
        choices=[(PENDING, "در انتظار بررسی"), (APPROVED, "تایید"), (REJECTED, "رد")],
        default=PENDING,
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_customer_review"),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), name="valid_review_rating"
            ),
        ]
        indexes = [models.Index(fields=["product", "status", "created"])]

    def __str__(self):
        return f"{self.product_id}: {self.rating}"
