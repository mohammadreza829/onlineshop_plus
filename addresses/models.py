from django.conf import settings
from django.db import models


class Address(models.Model):
    PROVINCE_CHOICES = (
        ("fars", "فارس"),
        ("tehran", "تهران"),
        ("isfahan", "اصفهان"),
        ("khorasan_razavi", "خراسان رضوی"),
        ("east_azerbaijan", "آذربایجان شرقی"),
        # سایر استان‌ها را می‌توانید اضافه کنید
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="addresses", on_delete=models.CASCADE, verbose_name="کاربر"
    )
    title = models.CharField(max_length=100, verbose_name="عنوان آدرس (مثلاً خانه، محل کار)")
    receiver_name = models.CharField(max_length=100, verbose_name="نام تحویل‌گیرنده")
    receiver_phone = models.CharField(max_length=20, verbose_name="شماره تماس تحویل‌گیرنده")
    province = models.CharField(max_length=50, choices=PROVINCE_CHOICES, default="fars", verbose_name="استان")
    city = models.CharField(max_length=100, verbose_name="شهر")
    full_address = models.TextField(verbose_name="آدرس دقیق پستی")
    postal_code = models.CharField(max_length=20, verbose_name="کد پستی")
    is_default = models.BooleanField(default=False, verbose_name="آدرس پیش‌فرض")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"

    def __str__(self):
        return f"{self.title} - {self.receiver_name}"

    def save(self, *args, **kwargs):
        # اگر این آدرس به عنوان پیش‌فرض انتخاب شده، بقیه آدرس‌های کاربر از حالت پیش‌فرض خارج شوند
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)
