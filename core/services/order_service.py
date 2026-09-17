from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F

from core.jalali import today_jalali
from core.models import Cart, Order, OrderItem, Product, User


class OrderService:
    @classmethod
    def _generate_order_code(cls) -> str:
        last_order = (
            Order.objects.filter(code__startswith="ORD-")
            .order_by("-id")
            .first()
        )
        if not last_order:
            return "ORD-9001"
        try:
            num = int(last_order.code.split("-")[1])
            return f"ORD-{num + 1:04d}"
        except (IndexError, ValueError):
            return f"ORD-{last_order.id + 9001:04d}"

    @classmethod
    def create_order(
        cls,
        items_data: list[dict[str, Any]],
        customer_name: str,
        phone: str = "",
        address: str = "",
        email: str = "",
        user: User | None = None,
        status: str = "در انتظار پردازش",
        payment: str = "در انتظار",
    ) -> Order:
        if not items_data:
            raise ValidationError("حداقل یک قلم کالا در سفارش الزامی است")

        if status not in Order.ORDER_STATUSES:
            raise ValidationError("وضعیت سفارش نامعتبر است")

        if payment not in Order.PAYMENT_STATUSES:
            raise ValidationError("وضعیت پرداخت نامعتبر است")

        quantities: dict[int, int] = {}
        for item in items_data:
            pid = item.get("product_id")
            qty = int(item.get("quantity", 1))
            if not pid or qty < 1:
                raise ValidationError("شناسه یا تعداد کالا نامعتبر است")
            quantities[pid] = quantities.get(pid, 0) + qty

        for attempt in range(5):
            try:
                with transaction.atomic():
                    products = list(
                        Product.objects.select_for_update().filter(id__in=quantities.keys())
                    )
                    if len(products) != len(quantities):
                        raise ValidationError("برخی از محصولات انتخابی در سیستم یافت نشدند")

                    for product in products:
                        required_qty = quantities[product.id]
                        if product.stock < required_qty:
                            raise ValidationError(
                                f"موجودی کالای «{product.name}» کافی نیست (موجودی: {product.stock})"
                            )

                    for product in products:
                        required_qty = quantities[product.id]
                        Product.objects.filter(id=product.id).update(
                            stock=F("stock") - required_qty
                        )

                    code = cls._generate_order_code()
                    order = Order.objects.create(
                        code=code,
                        user=user if (user and user.is_authenticated) else None,
                        customer=customer_name.strip() or "مشتری مهمان",
                        phone=phone.strip(),
                        email=email.strip(),
                        address=address.strip(),
                        date=today_jalali(),
                        status=status,
                        payment=payment,
                    )

                    for product in products:
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            product_name=product.name,
                            price=product.price,
                            quantity=quantities[product.id],
                        )

                    return order
            except IntegrityError:
                if attempt == 4:
                    raise ValidationError("خطا در ایجاد شناسه یکتای سفارش")

        raise ValidationError("خطا در ثبت سفارش")

    @classmethod
    def checkout_cart(
        cls,
        cart: Cart,
        customer_name: str,
        phone: str = "",
        address: str = "",
        email: str = "",
        user: User | None = None,
    ) -> Order:
        items = list(cart.items.all())
        if not items:
            raise ValidationError("سبد خرید خالی است")

        items_data = [
            {"product_id": item.product_id, "quantity": item.quantity}
            for item in items
        ]

        order = cls.create_order(
            items_data=items_data,
            customer_name=customer_name,
            phone=phone,
            address=address,
            email=email,
            user=user or cart.user,
        )

        cart.items.all().delete()
        return order

    @classmethod
    @transaction.atomic
    def update_status(cls, order: Order, new_status: str) -> Order:
        if new_status not in Order.ORDER_STATUSES:
            raise ValidationError("وضعیت مشخص شده معتبر نیست")

        old_status = order.status
        if old_status == new_status:
            return order

        if new_status == "لغو شده" and old_status != "لغو شده":
            for item in order.order_items.all():
                if item.product_id:
                    Product.objects.filter(id=item.product_id).update(
                        stock=F("stock") + item.quantity
                    )

        order.status = new_status
        order.save(update_fields=["status"])
        return order
