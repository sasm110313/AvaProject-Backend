import json
import os
from typing import Any

from django.db.models import Q, QuerySet

from core.jalali import random_name
from core.models import Product, ProductImage


class ProductService:
    @classmethod
    def list_products(
        cls,
        category: str | None = None,
        search: str | None = None,
    ) -> QuerySet[Product]:
        qs = Product.objects.all().prefetch_related("product_images")
        if category:
            qs = qs.filter(category=category)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(sku__icontains=search))
        return qs

    @classmethod
    def get_product(cls, product_id: int) -> Product:
        return Product.objects.prefetch_related("product_images").get(pk=product_id)

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
                image=random_name("products/images", uploaded.name),
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
