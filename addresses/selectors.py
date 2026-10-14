from .models import Address


def addresses_for_user(user):
    return Address.objects.filter(user=user) if user.is_authenticated else Address.objects.none()
