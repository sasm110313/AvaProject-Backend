import random
import re
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import MAX_OTP_ATTEMPTS, OtpCode, User


class AuthService:
    PHONE_REGEX = re.compile(r"^(?:0|\+98)?9\d{9}$")

    @classmethod
    def normalize_phone(cls, phone: str) -> str:
        phone = phone.strip()
        if phone.startswith("+98"):
            phone = "0" + phone[3:]
        elif phone.startswith("98"):
            phone = "0" + phone[2:]
        elif not phone.startswith("0") and len(phone) == 10:
            phone = "0" + phone
        return phone

    @classmethod
    def request_otp(cls, raw_phone: str) -> dict[str, Any]:
        phone = cls.normalize_phone(raw_phone)
        if not cls.PHONE_REGEX.match(phone):
            raise ValidationError("شماره موبایل وارد شده معتبر نیست")

        recent_otp = (
            OtpCode.objects.filter(phone=phone)
            .order_by("-created_at")
            .first()
        )
        if recent_otp and (timezone.now() - recent_otp.created_at).total_seconds() < 60:
            raise ValidationError("لطفاً یک دقیقه تا درخواست کد جدید صبر کنید")

        OtpCode.objects.filter(phone=phone).delete()
        code = str(random.randint(10000, 99999))
        OtpCode.objects.create(phone=phone, code=code)

        result: dict[str, Any] = {"success": True}
        if settings.DEBUG:
            result["devCode"] = code
        return result

    @classmethod
    def verify_otp(cls, raw_phone: str, code: str, session_key: str | None = None) -> dict[str, Any]:
        phone = cls.normalize_phone(raw_phone)
        code = code.strip()

        otp = OtpCode.objects.filter(phone=phone).order_by("-id").first()
        if not otp or otp.is_expired():
            raise ValidationError("کد منقضی شده است")

        if otp.failed_attempts >= MAX_OTP_ATTEMPTS:
            raise ValidationError("تلاش بیش از حد مجاز")

        if otp.code != code:
            otp.failed_attempts += 1
            otp.save(update_fields=["failed_attempts"])
            raise ValidationError("کد وارد شده صحیح نیست")

        otp.delete()

        user, _ = User.objects.get_or_create(phone=phone, defaults={"name": "کاربر"})

        if session_key:
            from .cart_service import CartService
            CartService.merge_guest_cart(user, session_key)

        refresh = RefreshToken.for_user(user)
        return {
            "success": True,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            "user": user,
        }
