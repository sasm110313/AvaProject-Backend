import os
import json
import logging
from django.core.management.base import BaseCommand
from django.core.files import File
from core.models import Product, ProductImage

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import scraped products from scraped_data/products.json into database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit the number of products to import (0 for all)"
        )
        parser.add_argument(
            "--with-images",
            action="store_true",
            help="Attach and copy local images into Django ProductImage media"
        )

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        json_path = os.path.join(base_dir, "scraped_data", "products.json")
        
        if not os.path.exists(json_path):
            self.stderr.write(self.style.ERROR(f"File not found: {json_path}"))
            return

        with open(json_path, "r", encoding="utf-8") as f:
            products_data = json.load(f)

        limit = options["limit"]
        if limit > 0:
            products_data = products_data[:limit]

        with_images = options["with_images"]
        self.stdout.write(self.style.NOTICE(f"Importing {len(products_data)} products..."))

        created_count = 0
        updated_count = 0

        for idx, item in enumerate(products_data, 1):
            title = (item.get("title") or "").strip()
            if not title:
                continue

            slug = item.get("slug") or f"prod-{idx}"
            sku = item.get("sku") or f"AVA-{slug[:80]}"
            category = item.get("category_name") or "عمومی"
            price = item.get("price_amount") or 10000000  # Default 10M if call-for-price
            short_desc = (item.get("short_description") or "").replace("\n", " ")[:250]
            
            product, created = Product.objects.update_or_create(
                sku=sku,
                defaults={
                    "name": title[:255],
                    "subtitle": short_desc,
                    "category": category[:100],
                    "price": price,
                    "stock": 10,
                    "threshold": 3,
                    "rating": 5.0,
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

            if with_images and item.get("local_images"):
                for rel_img_path in item["local_images"]:
                    full_img_path = os.path.join(base_dir, "scraped_data", rel_img_path)
                    if os.path.exists(full_img_path):
                        filename = os.path.basename(full_img_path)
                        # Check if already added
                        if not product.product_images.filter(original_name=filename).exists():
                            with open(full_img_path, "rb") as img_file:
                                p_img = ProductImage(product=product, original_name=filename)
                                p_img.image.save(filename, File(img_file), save=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully imported products! Created: {created_count}, Updated: {updated_count}"
            )
        )
