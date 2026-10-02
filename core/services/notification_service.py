from typing import Any
from django.db.models import QuerySet

from core.models import Notification, Order, User


class NotificationService:
    @classmethod
    def get_user_notifications(cls, user: User) -> QuerySet[Notification]:
        return Notification.objects.filter(user=user).order_by("-id")

    @classmethod
    def create_notification(
        cls,
        user: User,
        title: str,
        message: str,
        notification_type: str = "order",
        link: str = "",
    ) -> Notification:
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )

    @classmethod
    def notify_order_status(cls, order: Order) -> Notification | None:
        if not order.user:
            return None

        status_messages = {
            "در انتظار پردازش": f"سفارش شما با شماره پیگیری {order.code} دریافت شد و در صف بررسی قرار گرفت.",
            "در حال ارسال": f"سفارش شما با شماره {order.code} بسته‌بندی شد و تحویل واحد ارسال گردید.",
            "تحویل شده": f"سفارش شما با شماره {order.code} با موفقیت تحویل داده شد. از خرید شما سپاسگزاریم!",
            "مرجوع شده": f"درخواست مرجوعی سفارش {order.code} ثبت شد و در حال پیگیری است.",
            "لغو شده": f"سفارش شما با شماره {order.code} لغو گردید.",
        }

        msg = status_messages.get(
            order.status,
            f"وضعیت سفارش {order.code} به «{order.status}» تغییر یافت.",
        )

        return cls.create_notification(
            user=order.user,
            title=f"به‌روزرسانی سفارش {order.code}",
            message=msg,
            notification_type="order",
            link=f"/profile?tab=Orders&order={order.code}",
        )
