import json
import os
from typing import Any

from django.db.models import F, Q, QuerySet

from core.jalali import random_name
from core.models import Product, ProductImage


class ProductService:
    @classmethod
    def list_products(
        cls,
        category: str | None = None,
        search: str | None = None,
        brand: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        in_stock: bool | None = None,
        is_featured: bool | None = None,
        ordering: str | None = None,
    ) -> QuerySet[Product]:
        qs = Product.objects.filter(is_active=True).prefetch_related("product_images", "reviews")

        if category:
            qs = qs.filter(
                Q(category__iexact=category)
                | Q(category_rel__slug=category)
                | Q(category_rel__name__iexact=category)
                | Q(category_rel__parent__name__iexact=category)
            )

        if brand:
            qs = qs.filter(brand__iexact=brand)

        if min_price is not None:
            qs = qs.filter(price__gte=min_price)

        if max_price is not None:
            qs = qs.filter(price__lte=max_price)

        if in_stock is True:
            qs = qs.filter(stock__gt=0)
        elif in_stock is False:
            qs = qs.filter(stock=0)

        if is_featured is not None:
            qs = qs.filter(is_featured=is_featured)

        if search:
            search = search.strip()
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(subtitle__icontains=search)
                | Q(sku__icontains=search)
                | Q(brand__icontains=search)
                | Q(description__icontains=search)
            )

        # Ordering
        if ordering == "price_asc":
            qs = qs.order_by("price")
        elif ordering == "price_desc":
            qs = qs.order_by("-price")
        elif ordering == "newest":
            qs = qs.order_by("-id")
        elif ordering == "popular":
            qs = qs.order_by("-views_count", "-sales_count", "-id")
        elif ordering == "rating":
            qs = qs.order_by("-rating", "-id")
        else:
            qs = qs.order_by("-id")

        return qs

    @classmethod
    def get_product(cls, product_id: int, track_view: bool = False) -> Product:
        product = Product.objects.prefetch_related("product_images", "reviews").get(pk=product_id)
        if track_view:
            Product.objects.filter(pk=product_id).update(views_count=F("views_count") + 1)
            product.refresh_from_db(fields=["views_count"])
        return product

    @classmethod
    def _normalize(cls, value: str) -> str:
        if "/media/" in value:
            return value.split("/media/", 1)[-1]
        return value

    @classmethod
    def handle_media(cls, product: Product, request: Any) -> None:
        if not request:
            return

        files = request.FILES
        try:
            raw_keep = request.data.get("existingImageUrls", "[]") or "[]"
            keep_urls = json.loads(raw_keep) if isinstance(raw_keep, str) else raw_keep
            keep_paths = {cls._normalize(u) for u in keep_urls}
        except (ValueError, TypeError):
            keep_paths = set()

        for img in product.product_images.all():
            if cls._normalize(img.image.url) not in keep_paths:
                img.delete()

        for uploaded in files.getlist("images"):
            ProductImage.objects.create(
                product=product,
                image=uploaded,
                original_name=uploaded.name,
            )

        video_file = files.get("video")
        keep_video = request.data.get("existingVideoUrl")

        if video_file:
            product.video.save(
                os.path.basename(random_name("products/videos", video_file.name)),
                video_file,
            )
        elif not keep_video and product.video:
            product.video.delete(save=True)
