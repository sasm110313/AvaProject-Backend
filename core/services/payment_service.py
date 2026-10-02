import uuid
from typing import Any
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import Order, PaymentTransaction, User
from core.services.notification_service import NotificationService
from core.services.sms_service import SmsService


class PaymentService:
    @classmethod
    @transaction.atomic
    def initiate_payment(
        cls,
        order: Order,
        gateway: str = "mock",
        user: User | None = None,
        callback_url: str | None = None,
    ) -> dict[str, Any]:
        if order.payment == "پرداخت شده":
            raise ValidationError("این سفارش قبلاً پرداخت شده است")

        if order.status == "لغو شده":
            raise ValidationError("سفارش لغو شده قابل پرداخت نیست")

        amount = order.total
        if amount <= 0:
            order.payment = "پرداخت شده"
            order.save(update_fields=["payment"])
            return {"payment_url": None, "authority": None, "status": "paid_free"}

        authority = f"AUTH-{uuid.uuid4().hex[:16].upper()}"

        transaction_obj = PaymentTransaction.objects.create(
            order=order,
            user=user or order.user,
            amount=amount,
            gateway=gateway,
            authority=authority,
            status="pending",
        )

        # In dev or mock mode, we point to our internal mock payment gateway
        if gateway == "mock" or settings.DEBUG:
            payment_url = f"/api/payment/mock-pay/{authority}"
        else:
            payment_url = f"https://payment.zarinpal.com/pg/StartPay/{authority}"

        return {
            "payment_url": payment_url,
            "authority": authority,
            "amount": amount,
            "order_code": order.code,
            "gateway": gateway,
        }

    @classmethod
    @transaction.atomic
    def verify_payment(
        cls,
        authority: str,
        status_param: str = "OK",
        card_pan: str = "",
    ) -> dict[str, Any]:
        tx = PaymentTransaction.objects.select_for_update().filter(authority=authority).first()
        if not tx:
            raise ValidationError("تراکنش پرداخت یافت نشد")

        if tx.status == "success":
            return {
                "success": True,
                "message": "این تراکنش قبلاً با موفقیت تأیید شده است",
                "order_code": tx.order.code,
                "ref_id": tx.ref_id,
                "amount": tx.amount,
            }

        order = tx.order

        if status_param.upper() in ("OK", "SUCCESS", "100"):
            ref_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
            tx.status = "success"
            tx.ref_id = ref_id
            tx.card_pan = card_pan or "6037-****-****-1234"
            tx.verified_at = timezone.now()
            tx.save()

            order.payment = "پرداخت شده"
            if order.status == "در انتظار پردازش":
                order.status = "در انتظار پردازش"
            order.save(update_fields=["payment", "status"])

            NotificationService.create_notification(
                user=order.user,
                title="پرداخت موفق سفارش",
                message=f"پرداخت سفارش {order.code} به مبلغ {tx.amount:,} تومان با موفقیت انجام شد. شماره پیگیری: {ref_id}",
                notification_type="order",
            )

            if order.phone:
                try:
                    SmsService.send_payment_receipt(
                        phone=order.phone,
                        order_code=order.code,
                        amount=tx.amount,
                        ref_id=ref_id,
                    )
                except Exception:
                    pass

            return {
                "success": True,
                "message": "پرداخت با موفقیت انجام و تأیید شد",
                "order_code": order.code,
                "ref_id": ref_id,
                "amount": tx.amount,
            }
        else:
            tx.status = "failed"
            tx.error_message = "پرداخت توسط کاربر لغو شد یا درگاه با خطا مواجه گردید"
            tx.save()

            return {
                "success": False,
                "message": "پرداخت ناموفق بود یا توسط کاربر لغو شد",
                "order_code": order.code,
                "amount": tx.amount,
            }
