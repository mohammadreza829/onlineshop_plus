from django.core.exceptions import ValidationError

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_postal_code(value):
    value = str(value or "").translate(_DIGITS).strip()
    if len(value) != 10 or not value.isascii() or not value.isdigit():
        raise ValidationError("کد پستی باید ۱۰ رقم باشد.")
    return value
