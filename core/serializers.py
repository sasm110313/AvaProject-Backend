import json
import os
from typing import Any

from django.db.models import Q
from rest_framework import serializers

from core.jalali import random_name
from core.models import (
    Address,
    Article,
    ArticleVideo,
    Cart,
    CartItem,
    Favorite,
    Order,
    Product,
    ProductImage,
    User,
)
from core.services.product_service import ProductService

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v", "mkv"}


def file_extension(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def validate_uploaded_files(request: Any, fields: dict[str, str]) -> dict[str, list[str]]:
    if not request:
        return {}
    errors: dict[str, list[str]] = {}
    files = request.FILES
    for uploaded in files.getlist(fields.get("images", "__none__")):
        if file_extension(uploaded.name) not in IMAGE_EXTENSIONS:
            errors.setdefault("images", []).append("فرمت عکس نامعتبر است")
    for uploaded in files.getlist(fields.get("videos", "__none__")):
        if file_extension(uploaded.name) not in VIDEO_EXTENSIONS:
            errors.setdefault("videos", []).append("فرمت ویدیو نامعتبر است")
    for single in ("video", "coverImage"):
        key = fields.get(single)
        if not key:
            continue
        uploaded = files.get(key)
        if uploaded:
            allowed = VIDEO_EXTENSIONS if single == "video" else IMAGE_EXTENSIONS
            if file_extension(uploaded.name) not in allowed:
                errors.setdefault(single, []).append("فرمت فایل نامعتبر است")
    return errors


class ProductSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="name", read_only=True)
    oldPrice = serializers.IntegerField(
        source="old_price", required=False, allow_null=True
    )
    discount = serializers.SerializerMethodField()
    Empressive = serializers.BooleanField(source="is_featured", required=False)
    status = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "title",
            "subtitle",
            "category",
            "sku",
            "price",
            "oldPrice",
            "discount",
            "rating",
            "Empressive",
            "stock",
            "status",
            "threshold",
            "images",
            "video",
        ]
        read_only_fields = ["id", "title", "discount", "status", "images", "video"]

    def get_discount(self, obj: Product) -> int:
        if obj.old_price and obj.old_price > obj.price:
            return int(round((obj.old_price - obj.price) / obj.old_price * 100))
        return 0

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        errors = validate_uploaded_files(
            self.context.get("request"),
            {"images": "images", "video": "video"},
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def get_status(self, obj: Product) -> str:
        return "فعال" if obj.stock > 0 else "ناموجود"

    def get_images(self, obj: Product) -> list[dict[str, Any]]:
        request = self.context.get("request")
        result = []
        for img in obj.product_images.all():
            url = img.image.url
            if request:
                url = request.build_absolute_uri(url)
            result.append({"id": img.id, "url": url, "name": img.original_name or ""})
        return result

    def get_video(self, obj: Product) -> dict[str, str] | None:
        if not obj.video:
            return None
        url = obj.video.url
        request = self.context.get("request")
        if request:
            url = request.build_absolute_uri(url)
        return {"url": url, "name": os.path.basename(obj.video.name)}

    def create(self, validated_data: dict[str, Any]) -> Product:
        product = Product.objects.create(**validated_data)
        ProductService.handle_media(product, self.context.get("request"))
        return product

    def update(self, instance: Product, validated_data: dict[str, Any]) -> Product:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        ProductService.handle_media(instance, self.context.get("request"))
        if hasattr(instance, "_prefetched_objects_cache"):
            instance._prefetched_objects_cache = {}
        return instance


class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="code", read_only=True)
    items = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "phone",
            "email",
            "address",
            "date",
            "items",
            "total",
            "status",
            "payment",
        ]
        read_only_fields = ["id", "items", "total"]

    def get_items(self, obj: Order) -> int:
        return obj.items

    def get_total(self, obj: Order) -> int:
        return obj.total


class CustomerSerializer(serializers.ModelSerializer):
    orders = serializers.SerializerMethodField()
    spent = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "phone", "email", "orders", "spent", "joined"]
        read_only_fields = ["id", "orders", "spent", "joined"]

    def get_orders(self, obj: User) -> int:
        return Order.objects.filter(
            Q(user=obj) | Q(phone=obj.phone) | Q(customer__iexact=obj.name)
        ).distinct().count()

    def get_spent(self, obj: User) -> int:
        orders = Order.objects.filter(
            Q(user=obj) | Q(phone=obj.phone) | Q(customer__iexact=obj.name)
        ).filter(payment="پرداخت شده").distinct()
        return sum(order.total for order in orders)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "title", "address", "postal_code", "is_default"]
        read_only_fields = ["id"]


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "product", "product_id", "created_at"]
        read_only_fields = ["id", "created_at"]


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    name = serializers.CharField(source="product.name", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    price = serializers.IntegerField(source="product.price", read_only=True)
    subtotal = serializers.IntegerField(read_only=True)
    stock = serializers.IntegerField(source="product.stock", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "name",
            "sku",
            "price",
            "quantity",
            "subtotal",
            "stock",
            "image",
        ]
        read_only_fields = ["id", "subtotal"]

    def get_image(self, obj: CartItem) -> str | None:
        first_img = obj.product.product_images.first()
        if not first_img:
            return None
        url = first_img.image.url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "total_items", "total_price", "items"]


class ArticleSerializer(serializers.ModelSerializer):
    publishedAt = serializers.CharField(
        source="published_at", required=False, allow_blank=True
    )
    coverImage = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "excerpt",
            "content",
            "category",
            "author",
            "publishedAt",
            "status",
            "coverImage",
            "videos",
        ]
        read_only_fields = ["id", "publishedAt", "coverImage", "videos"]

    def get_coverImage(self, obj: Article) -> dict[str, str] | None:
        if not obj.cover_image:
            return None
        url = obj.cover_image.url
        request = self.context.get("request")
        if request:
            url = request.build_absolute_uri(url)
        return {"url": url, "name": os.path.basename(obj.cover_image.name)}

    def get_videos(self, obj: Article) -> list[dict[str, Any]]:
        request = self.context.get("request")
        result = []
        for video in obj.article_videos.all():
            url = video.video.url
            if request:
                url = request.build_absolute_uri(url)
            result.append({"id": video.id, "url": url, "name": video.original_name or ""})
        return result

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        errors = validate_uploaded_files(
            self.context.get("request"),
            {"coverImage": "coverImage", "videos": "videos"},
        )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _normalize(self, value: str) -> str:
        if "/media/" in value:
            return value.split("/media/", 1)[-1]
        return value

    def create(self, validated_data: dict[str, Any]) -> Article:
        article = Article.objects.create(**validated_data)
        self._handle_files(article, self.context.get("request"))
        return article

    def update(self, instance: Article, validated_data: dict[str, Any]) -> Article:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._handle_files(instance, self.context.get("request"))
        if hasattr(instance, "_prefetched_objects_cache"):
            instance._prefetched_objects_cache = {}
        return instance

    def _handle_files(self, article: Article, request: Any) -> None:
        if not request:
            return
        files = request.FILES
        cover_file = files.get("coverImage")
        keep_cover = request.data.get("existingCoverImageUrl")
        if cover_file:
            article.cover_image.save(
                os.path.basename(random_name("articles/covers", cover_file.name)),
                cover_file,
            )
        elif not keep_cover and article.cover_image:
            article.cover_image.delete(save=True)

        try:
            raw_keep = request.data.get("existingVideoUrls", "[]") or "[]"
            keep_urls = json.loads(raw_keep) if isinstance(raw_keep, str) else raw_keep
            keep_paths = {self._normalize(u) for u in keep_urls}
        except (ValueError, TypeError):
            keep_paths = set()

        for video in article.article_videos.all():
            if self._normalize(video.video.url) not in keep_paths:
                video.delete()

        for uploaded in files.getlist("videos"):
            ArticleVideo.objects.create(
                article=article,
                video=random_name("articles/videos", uploaded.name),
                original_name=uploaded.name,
            )


class ProfileSerializer(serializers.Serializer):
    NameAndFamily = serializers.CharField(max_length=255, required=False, allow_blank=True)
    BirthDate = serializers.CharField(max_length=30, required=False, allow_blank=True)
    IdCard = serializers.CharField(max_length=30, required=False, allow_blank=True)
    Email = serializers.EmailField(required=False, allow_blank=True)
    Number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)