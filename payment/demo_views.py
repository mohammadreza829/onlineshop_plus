import ipaddress

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import Payment


@require_http_methods(["GET", "POST"])
def demo_payment(request, authority):
    try:
        loopback = ipaddress.ip_address(request.META.get("REMOTE_ADDR", "")).is_loopback
    except ValueError:
        loopback = False
    if not settings.DEBUG or not getattr(settings, "LOCAL_DEMO", False) or not loopback:
        raise Http404
    payment = get_object_or_404(Payment, authority=authority, gateway="demo")
    if request.method == "POST":
        outcome = request.POST.get("outcome")
        if outcome not in ("success", "failed", "unknown"):
            raise Http404
        Payment.objects.filter(pk=payment.pk, status__in=["pending", "unknown"]).update(
            raw_response={"demo": True, "demo_outcome": outcome}
        )
        # This is a fake browser callback; only server verification decides the result.
        return redirect(reverse("payment:verify") + "?Authority=" + authority)
    return render(request, "payment/demo_payment.html", {"payment": payment})
