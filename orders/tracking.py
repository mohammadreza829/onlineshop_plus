"""Durable in-app notifications are committed atomically with order transitions."""

from .models import OrderEvent, OrderNotification


def record_event(order, *, previous_status="", kind="status"):
    # Caller owns the order row lock (or just created it) in an atomic transaction.
    order.event_sequence += 1
    order.save(update_fields=["event_sequence"])
    event = OrderEvent.objects.create(
        order=order,
        sequence=order.event_sequence,
        previous_status=previous_status,
        status=order.status,
        kind=kind,
        carrier=order.carrier,
        tracking_code=order.tracking_code,
    )
    if order.user_id:
        OrderNotification.objects.create(user_id=order.user_id, event=event)
    return event


def transition(order, new_status):
    previous = order.status
    order.transition_to(new_status)
    record_event(order, previous_status=previous)
