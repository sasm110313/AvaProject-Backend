from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Cart, CartItem, Product, User


class CartService:
    @classmethod
    def get_or_create_cart(
        cls,
        user: User | None = None,
        session_key: str | None = None,
    ) -> Cart:
        if user and user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=user)
            return cart

        if session_key:
            cart, _ = Cart.objects.get_or_create(session_key=session_key)
            return cart

        raise ValidationError("شناسه کاربر یا نشست کاربری الزامی است")

    @classmethod
    def add_item(
        cls,
        cart: Cart,
        product_id: int,
        quantity: int = 1,
    ) -> CartItem:
        if quantity <= 0:
            raise ValidationError("تعداد نامعتبر است")

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise ValidationError("محصول مورد نظر یافت نشد")

        if product.stock < quantity:
            raise ValidationError("موجودی محصول در انبار کافی نیست")

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            new_quantity = item.quantity + quantity
            if new_quantity > product.stock:
                raise ValidationError("تعداد درخواستی بیش از موجودی انبار است")
            item.quantity = new_quantity
            item.save(update_fields=["quantity", "updated_at"])

        return item

    @classmethod
    def update_item(
        cls,
        cart: Cart,
        product_id: int,
        quantity: int,
    ) -> CartItem | None:
        try:
            item = CartItem.objects.select_related("product").get(
                cart=cart,
                product_id=product_id,
            )
        except CartItem.DoesNotExist:
            raise ValidationError("کالا در سبد خرید یافت نشد")

        if quantity <= 0:
            item.delete()
            return None

        if quantity > item.product.stock:
            raise ValidationError("تعداد درخواستی بیش از موجودی انبار است")

        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])
        return item

    @classmethod
    def remove_item(cls, cart: Cart, product_id: int) -> None:
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()

    @classmethod
    def clear_cart(cls, cart: Cart) -> None:
        cart.items.all().delete()

    @classmethod
    @transaction.atomic
    def merge_guest_cart(cls, user: User, session_key: str) -> Cart:
        guest_cart = Cart.objects.filter(session_key=session_key).first()
        user_cart, _ = Cart.objects.get_or_create(user=user)

        if not guest_cart:
            return user_cart

        guest_items = list(guest_cart.items.select_related("product"))
        for g_item in guest_items:
            product = g_item.product
            u_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                product=product,
                defaults={"quantity": min(g_item.quantity, product.stock)},
            )
            if not created:
                combined = min(u_item.quantity + g_item.quantity, product.stock)
                u_item.quantity = combined
                u_item.save(update_fields=["quantity", "updated_at"])

        guest_cart.delete()
        return user_cart

    @classmethod
    def get_cart_summary(cls, cart: Cart, request: Any = None) -> dict[str, Any]:
        items_data = []
        items = cart.items.select_related("product").prefetch_related("product__product_images")

        for item in items:
            image_url = None
            first_img = item.product.product_images.first()
            if first_img:
                image_url = first_img.image.url
                if request:
                    image_url = request.build_absolute_uri(image_url)

            items_data.append(
                {
                    "id": item.id,
                    "product_id": item.product.id,
                    "name": item.product.name,
                    "sku": item.product.sku,
                    "price": item.product.price,
                    "quantity": item.quantity,
                    "subtotal": item.subtotal,
                    "stock": item.product.stock,
                    "image": image_url,
                }
            )

        return {
            "id": cart.id,
            "total_items": cart.total_items,
            "total_price": cart.total_price,
            "items": items_data,
        }
