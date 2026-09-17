from typing import Any

from django.db.models import Count, F, Sum

from core.models import Order, OrderItem, Product, User


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

        return {
            "summary": {
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "total_products": total_products,
                "low_stock_count": low_stock_count,
                "total_customers": total_customers,
            },
            "orders_by_status": status_counts,
            "low_stock_alerts": low_stock_items,
            "recent_orders": recent_orders,
            "top_selling_products": top_selling,
            "sales_trend": sorted_trend,
        }
