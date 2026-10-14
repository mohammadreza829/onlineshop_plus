from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.exceptions import APIException, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from account import otp
from account.services import authenticate_otp

from .serializers import (
    MessageSerializer,
    OTPVerifySerializer,
    PhoneSerializer,
    RefreshInputSerializer,
    TokenPairSerializer,
)


class SMSUnavailable(APIException):
    status_code = 503
    default_detail = "ارسال پیامک موقتاً در دسترس نیست."
    default_code = "sms_unavailable"


class PublicAuthView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "auth"


class OTPRequestView(PublicAuthView):
    @extend_schema(request=PhoneSerializer, responses={202: MessageSerializer}, tags=["Authentication"])
    def post(self, request):
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            otp.send_code(serializer.validated_data["phone"], ip=request.META.get("REMOTE_ADDR"))
        except otp.OTPUnavailable as exc:
            raise SMSUnavailable(detail=str(exc)) from exc
        except otp.OTPError as exc:
            if exc.retry_after:
                raise Throttled(wait=exc.retry_after, detail=str(exc)) from exc
            raise SMSUnavailable(detail=str(exc)) from exc
        return Response({"detail": "درخواست ارسال کد ثبت شد."}, status=status.HTTP_202_ACCEPTED)


class OTPVerifyView(PublicAuthView):
    @extend_schema(request=OTPVerifySerializer, responses={200: TokenPairSerializer}, tags=["Authentication"])
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = authenticate_otp(**serializer.validated_data)
        except otp.OTPUnavailable as exc:
            raise SMSUnavailable(detail=str(exc)) from exc
        except otp.OTPError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


@extend_schema_view(post=extend_schema(tags=["Authentication"]))
class RefreshView(TokenRefreshView):
    throttle_scope = "auth"


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "auth"

    @extend_schema(request=RefreshInputSerializer, responses={204: None}, tags=["Authentication"])
    def post(self, request):
        serializer = RefreshInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token["user_id"]) != str(request.user.pk):
                raise ValidationError({"detail": _("Invalid token.")})
            token.blacklist()
        except TokenError as exc:
            raise ValidationError({"detail": _("Invalid token.")}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
