from typing import Any

from django.db.models import Count, F, Sum

from core.models import (
    ContactMessage,
    Coupon,
    Order,
    OrderItem,
    Product,
    ProductQuestion,
    ProductReview,
    SmsLog,
    User,
)


class AnalyticsService:
    @classmethod
    def get_dashboard_metrics(cls) -> dict[str, Any]:
        orders_qs = Order.objects.prefetch_related("order_items")

        paid_orders = [o for o in orders_qs if o.payment == "پرداخت شده"]
        total_revenue = sum(o.total for o in paid_orders)

        total_orders = orders_qs.count()

        status_counts = {status: 0 for status in Order.ORDER_STATUSES}
        for item in orders_qs.values("status").annotate(count=Count("id")):
            if item["status"] in status_counts:
                status_counts[item["status"]] = item["count"]

        products_qs = Product.objects.all()
        total_products = products_qs.count()

        low_stock_qs = products_qs.filter(stock__lte=F("threshold"))
        low_stock_count = low_stock_qs.count()
        low_stock_items = list(
            low_stock_qs.values("id", "name", "stock", "threshold")[:10]
        )

        total_customers = User.objects.filter(is_staff=False).count()

        recent_orders_raw = orders_qs.order_by("-id")[:6]
        recent_orders = [
            {
                "id": o.code,
                "customer": o.customer,
                "date": o.date,
                "items": o.items,
                "total": o.total,
                "status": o.status,
                "payment": o.payment,
            }
            for o in recent_orders_raw
        ]

        top_selling = list(
            OrderItem.objects.values("product_id", "product_name")
            .annotate(total_sold=Sum("quantity"))
            .order_by("-total_sold")[:5]
        )

        sales_by_date = {}
        for o in paid_orders:
            sales_by_date[o.date] = sales_by_date.get(o.date, 0) + o.total

        sorted_trend = [
            {"date": k, "sales": v}
            for k, v in sorted(sales_by_date.items(), key=lambda x: x[0])
        ]

        from core.jalali import JALALI_MONTHS
        monthly_map = {m: 0 for m in JALALI_MONTHS}
        for o in paid_orders:
            try:
                parts = o.date.split("/")
                if len(parts) >= 2:
                    m_idx = int(parts[1]) - 1
                    if 0 <= m_idx < 12:
                        monthly_map[JALALI_MONTHS[m_idx]] += o.total
            except (ValueError, IndexError):
                pass

        sales_by_month = [{"month": m, "sales": monthly_map[m]} for m in JALALI_MONTHS]

        from core.models import Category
        cat_counts = Category.objects.filter(is_active=True).annotate(
            prod_count=Count("products")
        ).values("name", "prod_count")
        category_share = [
            {"name": item["name"], "value": item["prod_count"]}
            for item in cat_counts if item["prod_count"] > 0
        ]
        if not category_share:
            cat_counts2 = Product.objects.filter(is_active=True).values("category").annotate(count=Count("id")).order_by("-count")[:6]
            category_share = [{"name": c["category"] or "سایر", "value": c["count"]} for c in cat_counts2]

        total_inventory_items = sum(p.stock for p in products_qs)
        total_inventory_value = sum(p.price * p.stock for p in products_qs)

        pending_reviews_count = ProductReview.objects.filter(is_approved=False).count()
        unanswered_questions_count = ProductQuestion.objects.filter(answers__isnull=True).count()
        pending_messages_count = ContactMessage.objects.filter(is_responded=False).count()
        active_coupons_count = Coupon.objects.filter(is_active=True).count()
        sms_total_sent = SmsLog.objects.filter(status__in=["sent", "delivered"]).count()
        sms_failed = SmsLog.objects.filter(status="failed").count()

        return {
            "summary": {
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "total_products": total_products,
                "low_stock_count": low_stock_count,
                "total_customers": total_customers,
                "total_inventory_items": total_inventory_items,
                "total_inventory_value": total_inventory_value,
                "pending_reviews_count": pending_reviews_count,
                "unanswered_questions_count": unanswered_questions_count,
                "pending_messages_count": pending_messages_count,
                "active_coupons_count": active_coupons_count,
                "sms_total_sent": sms_total_sent,
                "sms_failed": sms_failed,
            },
            "orders_by_status": status_counts,
            "low_stock_alerts": low_stock_items,
            "recent_orders": recent_orders,
            "top_selling_products": top_selling,
            "sales_trend": sorted_trend,
            "sales_by_month": sales_by_month,
            "category_share": category_share,
        }
