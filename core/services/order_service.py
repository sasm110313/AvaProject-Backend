from typing import Any
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F

from core.jalali import today_jalali
from core.models import Cart, Order, OrderItem, OrderStatusHistory, Product, ProductVariant, SiteSetting, User
from core.services.coupon_service import CouponService
from core.services.notification_service import NotificationService


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
        coupon_code: str = "",
        shipping_cost: int = 0,
        shipping_method: str = "پست پیشتاز",
        customer_notes: str = "",
    ) -> Order:
        if not items_data:
            raise ValidationError("حداقل یک قلم کالا در سفارش الزامی است")

        if status not in Order.ORDER_STATUSES:
            raise ValidationError(f"وضعیت سفارش نامعتبر است. وضعیت‌های مجاز: {', '.join(Order.ORDER_STATUSES)}")

        if payment not in Order.PAYMENT_STATUSES:
            raise ValidationError(f"وضعیت پرداخت نامعتبر است. وضعیت‌های مجاز: {', '.join(Order.PAYMENT_STATUSES)}")

        product_quantities: dict[int, int] = {}
        variant_quantities: dict[int, int] = {}
        parsed_items: list[dict[str, Any]] = []

        for item in items_data:
            pid = item.get("product_id")
            vid = item.get("variant_id")
            qty = int(item.get("quantity", 1))
            if not pid or qty < 1:
                raise ValidationError("شناسه یا تعداد کالا نامعتبر است")
            product_quantities[pid] = product_quantities.get(pid, 0) + qty
            if vid:
                variant_quantities[vid] = variant_quantities.get(vid, 0) + qty
            parsed_items.append({"product_id": pid, "variant_id": vid, "quantity": qty})

        for attempt in range(5):
            try:
                with transaction.atomic():
                    products = {
                        p.id: p
                        for p in Product.objects.select_for_update().filter(id__in=product_quantities.keys())
                    }
                    if len(products) != len(product_quantities):
                        raise ValidationError("برخی از محصولات انتخابی در سیستم یافت نشدند")

                    for pid, req_qty in product_quantities.items():
                        product = products[pid]
                        if product.stock < req_qty:
                            raise ValidationError(
                                f"موجودی کالای «{product.name}» کافی نیست (موجودی: {product.stock})"
                            )

                    variants: dict[int, ProductVariant] = {}
                    if variant_quantities:
                        variants = {
                            v.id: v
                            for v in ProductVariant.objects.select_for_update().filter(id__in=variant_quantities.keys())
                        }
                        for vid, req_qty in variant_quantities.items():
                            variant = variants.get(vid)
                            if not variant:
                                raise ValidationError("برخی از تنوع‌های انتخابی یافت نشدند")
                            if variant.stock < req_qty:
                                raise ValidationError(
                                    f"موجودی تنوع «{variant.title}» کافی نیست (موجودی: {variant.stock})"
                                )

                    # Deduct stock and increment sales_count
                    for pid, req_qty in product_quantities.items():
                        Product.objects.filter(id=pid).update(
                            stock=F("stock") - req_qty,
                            sales_count=F("sales_count") + req_qty,
                        )

                    for vid, req_qty in variant_quantities.items():
                        ProductVariant.objects.filter(id=vid).update(
                            stock=F("stock") - req_qty
                        )

                    # Calculate total before discounts
                    raw_total = 0
                    for item in parsed_items:
                        prod = products[item["product_id"]]
                        var = variants.get(item["variant_id"]) if item["variant_id"] else None
                        unit_p = var.price if var else prod.price
                        raw_total += unit_p * item["quantity"]

                    # Calculate shipping cost from SiteSetting if not set
                    if shipping_cost == 0 and raw_total > 0:
                        setting = SiteSetting.get_settings()
                        if raw_total < setting.free_shipping_threshold:
                            shipping_cost = setting.default_shipping_cost

                    # Check coupon if provided
                    discount_amount = 0
                    valid_coupon = None
                    if coupon_code:
                        coupon_res = CouponService.validate_coupon(
                            code=coupon_code,
                            user=user,
                            total_amount=raw_total,
                        )
                        discount_amount = coupon_res["discount_amount"]
                        valid_coupon = coupon_res["coupon"]

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
                        shipping_cost=shipping_cost,
                        shipping_method=shipping_method,
                        discount_amount=discount_amount,
                        coupon_code=valid_coupon.code if valid_coupon else "",
                        customer_notes=customer_notes.strip(),
                    )

                    for item in parsed_items:
                        prod = products[item["product_id"]]
                        var = variants.get(item["variant_id"]) if item["variant_id"] else None
                        unit_p = var.price if var else prod.price
                        OrderItem.objects.create(
                            order=order,
                            product=prod,
                            variant=var,
                            variant_title=var.title if var else "",
                            product_name=prod.name,
                            price=unit_p,
                            quantity=item["quantity"],
                        )

                    if valid_coupon:
                        CouponService.apply_to_order(
                            coupon=valid_coupon,
                            order=order,
                            user=user,
                            discount_amount=discount_amount,
                        )

                    # Initial status history
                    OrderStatusHistory.objects.create(
                        order=order,
                        from_status="",
                        to_status=status,
                        comment="ثبت سفارش اولیه",
                    )

                    # Send notification to user
                    NotificationService.notify_order_status(order)

                    # Send SMS confirmation
                    if order.phone:
                        from core.services.sms_service import SmsService
                        SmsService.send_order_placed(order.phone, order.code, order.total)

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
        coupon_code: str = "",
        shipping_method: str = "پست پیشتاز",
        customer_notes: str = "",
    ) -> Order:
        items = list(cart.items.select_related("product", "variant"))
        if not items:
            raise ValidationError("سبد خرید خالی است")

        effective_coupon = coupon_code or (cart.coupon.code if cart.coupon else "")

        items_data = [
            {
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "quantity": item.quantity,
            }
            for item in items
        ]

        order = cls.create_order(
            items_data=items_data,
            customer_name=customer_name,
            phone=phone,
            address=address,
            email=email,
            user=user or cart.user,
            coupon_code=effective_coupon,
            shipping_method=shipping_method,
            customer_notes=customer_notes,
        )

        cart.items.all().delete()
        if cart.coupon:
            cart.coupon = None
            cart.save(update_fields=["coupon"])

        return order

    @classmethod
    @transaction.atomic
    def update_status(cls, order: Order, new_status: str, comment: str = "") -> Order:
        if new_status not in Order.ORDER_STATUSES:
            raise ValidationError(
                f"وضعیت مشخص شده معتبر نیست. وضعیت‌های مجاز: {', '.join(Order.ORDER_STATUSES)}"
            )

        old_status = order.status
        if old_status == new_status:
            return order

        # Restore stock if canceled or returned
        if new_status in ("لغو شده", "مرجوع شده") and old_status not in ("لغو شده", "مرجوع شده"):
            for item in order.order_items.all():
                if item.product_id:
                    Product.objects.filter(id=item.product_id).update(
                        stock=F("stock") + item.quantity,
                        sales_count=F("sales_count") - item.quantity,
                    )
                if item.variant_id:
                    ProductVariant.objects.filter(id=item.variant_id).update(
                        stock=F("stock") + item.quantity,
                    )

        order.status = new_status
        order.save(update_fields=["status"])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status=new_status,
            comment=comment or f"تغییر وضعیت به {new_status}",
        )

        NotificationService.notify_order_status(order)

        if order.phone:
            from core.services.sms_service import SmsService
            SmsService.send_order_status(order.phone, order.code, new_status, order.tracking_code)

        return order
