from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# ==========================================
# Category
# ==========================================

class Category(models.Model):

    name = models.CharField(
        max_length=50,
        verbose_name='دسته بندی محصولات'
    )

    slug = models.SlugField(
        max_length=250,
        unique=True,
        db_index=True
    )

    parent = models.ForeignKey(
        'self',
        related_name='children',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='دسته والد'
    )

    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )

    updated = models.DateTimeField(
        auto_now=True,
        verbose_name='تاریخ بروزرسانی'
    )

    class Meta:
        ordering = ['name']

        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['parent']),
        ]

        verbose_name = 'دسته بندی'
        verbose_name_plural = 'دسته بندی ها'

    def __str__(self):
        return self.name


# ==========================================
# Product
# ==========================================

class Product(models.Model):

    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='دسته بندی'
    )

    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='کد محصول'
    )

    name = models.CharField(
        max_length=250,
        verbose_name='نام محصول'
    )

    slug = models.SlugField(
        max_length=250,
        unique=True,
        db_index=True
    )

    description = models.TextField(
        blank=True,
        verbose_name='توضیحات'
    )

    inventory = models.PositiveIntegerField(
        default=0,
        verbose_name='موجودی'
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='قیمت'
    )

    off = models.PositiveIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        verbose_name='درصد تخفیف'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال'
    )

    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )

    updated = models.DateTimeField(
        auto_now=True,
        verbose_name='تاریخ بروزرسانی'
    )
    weight = models.DecimalField(
        default=1, max_digits=100, decimal_places=0, verbose_name='وزن')

    class Meta:

        ordering = ['-created']

        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]

        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'

    def __str__(self):
        return self.name

    @property
    def final_price(self):

        if self.off >= 100:
            return 0

        return self.price - (
            self.price * self.off / 100
        )


# ==========================================
# Product Features
# ==========================================

class ProductFeatures(models.Model):

    product = models.ForeignKey(
        Product,
        related_name='features',
        on_delete=models.CASCADE,
        verbose_name='محصول'
    )

    name = models.CharField(
        max_length=250,
        verbose_name='مشخصات'
    )

    value = models.CharField(
        max_length=250,
        verbose_name='مقدار ویژگی'
    )

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'product',
                    'name',
                    'value'
                ],
                name='unique_product_feature'
            )
        ]

        verbose_name = 'ویژگی محصول'
        verbose_name_plural = 'ویژگی های محصول'

    def __str__(self):
        return f'{self.name}: {self.value}'


# ==========================================
# Product Images
# ==========================================

class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        related_name='images',
        on_delete=models.CASCADE,
        verbose_name='محصول'
    )

    image = models.ImageField(
        upload_to='products/',
        verbose_name='تصویر'
    )

    description = models.CharField(
        max_length=250,
        blank=True,
        verbose_name='توضیحات تصویر'
    )

    is_primary = models.BooleanField(
        default=False,
        verbose_name='تصویر اصلی'
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name='ترتیب نمایش'
    )

    class Meta:

        ordering = ['order']

        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_primary=True),
                name='unique_primary_product_image'
            )
        ]

        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصول'

    def __str__(self):
        return self.description or f'Image #{self.id}'
