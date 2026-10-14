from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import CouponUse, Order, OrderEvent, OrderNotification
from orders.selectors import orders_for_user
from orders.serializers import OrderDetailSerializer
from orders.services import OrderActionError, advance_order, update_shipping
from payment.models import Payment

from .operation_permissions import CanManageOrders, CanViewSales


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderEvent
        fields = [
            "id",
            "sequence",
            "kind",
            "previous_status",
            "status",
            "carrier",
            "tracking_code",
            "created",
        ]
        read_only_fields = fields


class TrackingView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EventSerializer

    def get_queryset(self):
        order = get_object_or_404(orders_for_user(self.request.user), pk=self.kwargs["pk"])
        return order.events.all()


class NotificationSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)
    order_id = serializers.IntegerField(source="event.order_id", read_only=True)
    order_number = serializers.CharField(source="event.order.order_number", read_only=True)

    class Meta:
        model = OrderNotification
        fields = ["id", "order_id", "order_number", "event", "read_at", "created"]
        read_only_fields = fields


class NotificationListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return OrderNotification.objects.filter(user=self.request.user).select_related("event__order")


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses=NotificationSerializer, tags=["Notifications"])
    def post(self, request, pk):
        notification = get_object_or_404(OrderNotification, user=request.user, pk=pk)
        OrderNotification.objects.filter(pk=pk, read_at__isnull=True).update(read_at=timezone.now())
        notification.refresh_from_db()
        return Response(NotificationSerializer(notification).data)


class StaffOrderInput(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[Order.STATUS_PREPARING, Order.STATUS_SENT, Order.STATUS_DELIVERED, Order.STATUS_CANCELED],
        required=False,
    )
    carrier = serializers.CharField(max_length=80, required=False)
    tracking_code = serializers.CharField(max_length=100, required=False)

    def validate(self, data):
        if not data:
            raise serializers.ValidationError("حداقل یک تغییر لازم است.")
        if ("carrier" in data) != ("tracking_code" in data):
            raise serializers.ValidationError("نام شرکت ارسال و کد رهگیری را با هم ارسال کنید.")
        return data


class StaffOrderView(APIView):
    permission_classes = [CanManageOrders]
    throttle_scope = "shop_write"

    @extend_schema(request=StaffOrderInput, responses=OrderDetailSerializer, tags=["Staff"])
    def post(self, request, pk):
        data = StaffOrderInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        try:
            with transaction.atomic():
                order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
                if values.get("status"):
                    order = advance_order(order, values["status"], actor=request.user)
                if "carrier" in values:
                    order = update_shipping(
                        order, carrier=values["carrier"], tracking_code=values["tracking_code"]
                    )
        except OrderActionError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(OrderDetailSerializer(order).data)


class DashboardFilter(serializers.Serializer):
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)

    def validate(self, data):
        today = timezone.localdate()
        first = data.get("from_date", today - timedelta(days=29))
        last = data.get("to_date", today)
        if first.year < 2 or last.year > 9998:
            raise serializers.ValidationError("تاریخ خارج از محدوده مجاز است.")
        if first > last or (last - first).days > 365:
            raise serializers.ValidationError("بازه باید مرتب و حداکثر ۳۶۶ روز باشد.")
        return {"from_date": first, "to_date": last}


class StatusCountSerializer(serializers.Serializer):
    status = serializers.CharField()
    total = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    time_zone = serializers.CharField()
    currency = serializers.CharField()
    orders_created = serializers.IntegerField()
    created_orders_by_status = StatusCountSerializer(many=True)
    paid_orders_count = serializers.IntegerField()
    paid_orders_value = serializers.DecimalField(max_digits=20, decimal_places=0)
    canceled_paid_orders_value = serializers.DecimalField(max_digits=20, decimal_places=0)
    successful_payment_amount = serializers.DecimalField(max_digits=20, decimal_places=0)
    duplicate_payment_refund_flag_amount = serializers.DecimalField(max_digits=20, decimal_places=0)
    needs_review_orders_all_time = serializers.IntegerField()
    coupon_over_capacity_all_time = serializers.IntegerField()
    unknown_payments_all_time = serializers.IntegerField()


class SalesDashboardView(APIView):
    permission_classes = [CanViewSales]

    @extend_schema(parameters=[DashboardFilter], responses=DashboardSerializer, tags=["Staff"])
    def get(self, request):
        params = DashboardFilter(data=request.query_params)
        params.is_valid(raise_exception=True)
        dates = params.validated_data
        first = timezone.make_aware(datetime.combine(dates["from_date"], time.min))
        last = timezone.make_aware(datetime.combine(dates["to_date"] + timedelta(days=1), time.min))
        created = Order.objects.filter(created__gte=first, created__lt=last)
        paid = Order.objects.filter(is_paid=True, paid_at__gte=first, paid_at__lt=last)
        successful = Payment.objects.filter(
            status=Payment.STATUS_SUCCESS, verified_at__gte=first, verified_at__lt=last
        )

        statuses = list(created.values("status").annotate(total=Count("pk")).order_by("status"))
        paid_totals = paid.aggregate(
            total=Count("pk"),
            value=Sum("total_price"),
            canceled_value=Sum("total_price", filter=Q(status=Order.STATUS_CANCELED)),
        )
        payment_totals = successful.aggregate(
            value=Sum("amount"), refund_value=Sum("amount", filter=Q(needs_refund=True))
        )
        return Response(
            {
                **dates,
                "time_zone": str(timezone.get_current_timezone()),
                "currency": "TOMAN",
                "orders_created": sum(row["total"] for row in statuses),
                "created_orders_by_status": statuses,
                "paid_orders_count": paid_totals["total"],
                "paid_orders_value": str(paid_totals["value"] or Decimal(0)),
                "canceled_paid_orders_value": str(paid_totals["canceled_value"] or Decimal(0)),
                "successful_payment_amount": str(payment_totals["value"] or Decimal(0)),
                "duplicate_payment_refund_flag_amount": str(payment_totals["refund_value"] or Decimal(0)),
                "needs_review_orders_all_time": Order.objects.filter(
                    status=Order.STATUS_NEEDS_REVIEW
                ).count(),
                "coupon_over_capacity_all_time": CouponUse.objects.filter(over_capacity=True).count(),
                "unknown_payments_all_time": Payment.objects.filter(status=Payment.STATUS_UNKNOWN).count(),
            }
        )
