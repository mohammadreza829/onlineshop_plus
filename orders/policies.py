"""Pure decisions; services enforce these again inside their transaction."""


def owns_order(user, order):
    return bool(user.is_authenticated and order.user_id == user.pk)


def may_cancel_order(user, order):
    return owns_order(user, order) and order.is_cancelable_by_user
