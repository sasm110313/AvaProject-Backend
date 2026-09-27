import hashlib
import json
import logging
import os
import re

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Product, ProductImage

logger = logging.getLogger(__name__)

DEFAULT_PRICE = 10000000
DEFAULT_STOCK = 10


def _safe(value, max_len):
    value = (value or "").strip()
    return value[:max_len]


def _make_sku(slug, url, seen_slugs):
    base = slug or ""
    if base in seen_slugs:
        digest = hashlib.md5((url or base).encode("utf-8")).hexdigest()[:6]
        base = f"{base}-{digest}"
    seen_slugs.add(slug or "")

    clean = re.sub(r"[^a-zA-Z0-9\-_]", "-", base)
    clean = re.sub(r"-{2,}", "-", clean).strip("-")
    sku = f"AVA-{clean}" if clean else f"AVA-{hashlib.md5((url or '').encode('utf-8')).hexdigest()[:10]}"
    if len(sku) > 100:
        digest = hashlib.md5((url or base).encode("utf-8")).hexdigest()[:10]
        sku = f"AVA-{clean[:78]}-{digest}"
    return sku[:100]


class Command(BaseCommand):
    help = "Import all scraped products from scraped_data/products.json into database (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit the number of products to import (0 means all).",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Do not copy/attach local scraped images.",
        )
        parser.add_argument(
            "--default-price",
            type=int,
            default=DEFAULT_PRICE,
            help="Price used for products without a parseable price (default 10000000).",
        )
        parser.add_argument(
            "--stock",
            type=int,
            default=DEFAULT_STOCK,
            help="Stock level for imported products (default 10).",
        )

    def handle(self, *args, **options):
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "scraped_data",
        )
        json_path = os.path.join(data_dir, "products.json")

        if not os.path.exists(json_path):
            self.stderr.write(self.style.ERROR(f"File not found: {json_path}"))
            return

        with open(json_path, "r", encoding="utf-8") as f:
            products_data = json.load(f)

        limit = options["limit"]
        if limit > 0:
            products_data = products_data[:limit]

        default_price = options["default_price"]
        stock = options["stock"]
        with_images = not options["skip_images"]

        self.stdout.write(
            self.style.NOTICE(
                f"Importing {len(products_data)} products | "
                f"default_price={default_price} stock={stock} images={'yes' if with_images else 'no'}"
            )
        )

        created = 0
        updated = 0
        failed = []
        seen_slugs = set()

        for idx, item in enumerate(products_data, 1):
            title = _safe(item.get("title"), 255)
            url = item.get("url") or ""
            if not title:
                failed.append((idx, f"empty title {url}"))
                continue

            slug = item.get("slug") or (url.strip("/").split("/")[-1] if url else f"prod-{idx}")
            sku = _make_sku(slug, url, seen_slugs)
            subtitle = _safe((item.get("short_description") or "").replace("\n", " "), 245)
            category = _safe(item.get("category_name") or item.get("category_key") or "عمومی", 100)
            price = item.get("price_amount") or default_price
            if price < 1:
                price = default_price

            defaults = {
                "name": title,
                "subtitle": subtitle,
                "category": category,
                "price": price,
                "stock": stock,
                "threshold": 3,
                "rating": 5.0,
                "old_price": None,
                "is_featured": False,
            }

            img_dir = os.path.join(data_dir, "images", slug)
            try:
                with transaction.atomic():
                    product, created_flag = Product.objects.update_or_create(
                        sku=sku, defaults=defaults
                    )
                    if with_images and os.path.isdir(img_dir):
                        self._attach_images(product, img_dir, sku)
                if created_flag:
                    created += 1
                else:
                    updated += 1
            except Exception as e:  # noqa: BLE001
                failed.append((idx, f"{sku}: {e}"))
                logger.exception("Failed importing product #%s %s", idx, sku)
                continue

            if idx % 50 == 0 or idx == len(products_data):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Progress {idx}/{len(products_data)} | created={created} updated={updated} failed={len(failed)}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"DONE: created={created} updated={updated} failed={len(failed)} of {len(products_data)}"
            )
        )
        if failed:
            for idx, reason in failed:
                self.stderr.write(self.style.ERROR(f"  FAILED #{idx}: {reason}"))

    def _attach_images(self, product, img_dir, sku):
        try:
            filenames = sorted(
                n
                for n in os.listdir(img_dir)
                if os.path.isfile(os.path.join(img_dir, n))
                and os.path.getsize(os.path.join(img_dir, n)) > 500
            )
        except OSError as e:
            logger.warning("Cannot read %s: %s", img_dir, e)
            return

        folder = hashlib.md5(sku.encode("utf-8")).hexdigest()[:8]
        existing = {i.image.name for i in product.product_images.all()}
        for idx, filename in enumerate(filenames, 1):
            ext = ""
            m = re.search(r"\.([a-z0-9]{2,5})$", filename.lower())
            if m:
                ext = f".{m.group(1)}"
            stored_name = f"products/images/imported/{folder}/{idx:02d}{ext}"
            if stored_name in existing:
                continue
            src_path = os.path.join(img_dir, filename)
            with open(src_path, "rb") as src:
                ProductImage.objects.create(
                    product=product,
                    image=File(src, name=f"imported/{folder}/{idx:02d}{ext}"),
                    original_name=filename,
                )