from typing import Any
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from core.models import Coupon, CouponUsage, Order, User


class CouponService:
    @classmethod
    def validate_coupon(
        cls,
        code: str,
        user: User | None = None,
        total_amount: int = 0,
    ) -> dict[str, Any]:
        code = code.strip().upper()
        if not code:
            raise ValidationError("کد تخفیف نمی‌تواند خالی باشد")

        coupon = Coupon.objects.filter(code__iexact=code).first()
        if not coupon:
            raise ValidationError("کد تخفیف معتبر نیست")

        if not coupon.is_valid_now():
            raise ValidationError("مهلت استفاده از این کد تخفیف به پایان رسیده یا غیرفعال است")

        if total_amount < coupon.min_purchase_amount:
            raise ValidationError(
                f"حداقل مبلغ خرید برای اعمال این کد تخفیف {coupon.min_purchase_amount:,} تومان است"
            )

        if user and user.is_authenticated:
            user_usages = CouponUsage.objects.filter(coupon=coupon, user=user).count()
            if user_usages >= coupon.per_user_limit:
                raise ValidationError("شما قبلاً از این کد تخفیف استفاده کرده‌اید")

        # Calculate discount
        if coupon.discount_type == "percent":
            calculated = (total_amount * coupon.discount_value) // 100
            if coupon.max_discount_amount:
                discount_amount = min(calculated, coupon.max_discount_amount)
            else:
                discount_amount = calculated
        else:
            discount_amount = min(coupon.discount_value, total_amount)

        final_total = max(0, total_amount - discount_amount)

        return {
            "valid": True,
            "coupon_code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": coupon.discount_value,
            "discount_amount": discount_amount,
            "original_total": total_amount,
            "final_total": final_total,
            "message": "کد تخفیف با موفقیت اعمال شد",
            "coupon": coupon,
        }

    @classmethod
    @transaction.atomic
    def apply_to_order(
        cls,
        coupon: Coupon,
        order: Order,
        user: User | None = None,
        discount_amount: int = 0,
    ) -> CouponUsage:
        usage = CouponUsage.objects.create(
            coupon=coupon,
            user=user if (user and user.is_authenticated) else None,
            order=order,
            discount_applied=discount_amount,
        )
        Coupon.objects.filter(pk=coupon.pk).update(used_count=F("used_count") + 1)
        return usage
