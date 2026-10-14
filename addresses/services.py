from django.core.exceptions import PermissionDenied
from django.db import transaction

from account.models import ShopUser

from .models import Address

EDITABLE_FIELDS = {
    "title",
    "receiver_name",
    "receiver_phone",
    "province",
    "city",
    "full_address",
    "postal_code",
    "is_default",
}


@transaction.atomic
def save_address(*, user, data, address=None):
    # Serialize default-address decisions, including concurrent first addresses.
    ShopUser.objects.select_for_update().get(pk=user.pk)
    if address is None:
        address = Address(user=user)
        first = not Address.objects.filter(user=user).exists()
    else:
        address = Address.objects.select_for_update().get(pk=address.pk)
        if address.user_id != user.pk:
            raise PermissionDenied
        first = False
    for key, value in data.items():
        if key in EDITABLE_FIELDS:
            setattr(address, key, value)
    if first:
        address.is_default = True
    address.save()
    return address
