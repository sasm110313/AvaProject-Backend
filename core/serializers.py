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
    Banner,
    Cart,
    CartItem,
    Category,
    ContactMessage,
    Coupon,
    Favorite,
    NewsletterSubscriber,
    Notification,
    Order,
    OrderItem,
    OrderStatusHistory,
    PaymentTransaction,
    Product,
    ProductAnswer,
    ProductImage,
    ProductQuestion,
    ProductReview,
    ProductVariant,
    SiteSetting,
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
    for single in ("video", "coverImage", "avatar", "categoryImage", "bannerImage"):
        key = fields.get(single)
        if not key:
            continue
        uploaded = files.get(key)
        if uploaded:
            allowed = VIDEO_EXTENSIONS if single == "video" else IMAGE_EXTENSIONS
            if file_extension(uploaded.name) not in allowed:
                errors.setdefault(single, []).append("فرمت فایل نامعتبر است")
    return errors


class CategorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon"]


class CategorySerializer(serializers.ModelSerializer):
    children = CategorySimpleSerializer(many=True, read_only=True)
    products_count = serializers.IntegerField(read_only=True, default=0)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "description",
            "icon",
            "image",
            "display_order",
            "is_active",
            "products_count",
            "children",
        ]
        read_only_fields = ["id", "products_count", "children"]

    def get_image(self, obj: Category) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    name = serializers.CharField(source="original_name", read_only=True)

    class Meta:
        model = ProductImage
        fields = ["id", "url", "name"]

    def get_url(self, obj: ProductImage) -> str:
        url = obj.image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class ProductVariantSerializer(serializers.ModelSerializer):
    price = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ["id", "title", "sku", "price", "price_override", "stock", "is_active"]
        read_only_fields = ["id", "price"]


class ProductReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReview
        fields = [
            "id",
            "product",
            "user_name",
            "rating",
            "comment",
            "pros",
            "cons",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProductAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAnswer
        fields = ["id", "user_name", "answer_text", "is_admin_answer", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductQuestionSerializer(serializers.ModelSerializer):
    answers = serializers.SerializerMethodField()

    class Meta:
        model = ProductQuestion
        fields = ["id", "product", "user_name", "question_text", "answers", "created_at"]
        read_only_fields = ["id", "answers", "created_at"]

    def get_answers(self, obj: ProductQuestion) -> list[dict[str, Any]]:
        approved_answers = obj.answers.filter(is_approved=True).order_by("id")
        return ProductAnswerSerializer(approved_answers, many=True).data


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
    reviews_count = serializers.SerializerMethodField()
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "title",
            "subtitle",
            "description",
            "brand",
            "specifications",
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
            "is_active",
            "views_count",
            "sales_count",
            "weight_grams",
            "reviews_count",
            "variants",
            "images",
            "video",
        ]
        read_only_fields = [
            "id",
            "title",
            "discount",
            "status",
            "images",
            "video",
            "views_count",
            "sales_count",
            "reviews_count",
            "variants",
        ]

    def get_discount(self, obj: Product) -> int:
        if obj.old_price and obj.old_price > obj.price:
            return int(round((obj.old_price - obj.price) / obj.old_price * 100))
        return 0

    def get_reviews_count(self, obj: Product) -> int:
        return obj.reviews.filter(is_approved=True).count()

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


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "variant",
            "variant_title",
            "product_name",
            "price",
            "quantity",
            "subtotal",
        ]
        read_only_fields = ["id", "subtotal"]


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["id", "from_status", "to_status", "comment", "created_at"]
        read_only_fields = ["id", "created_at"]


class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="code", read_only=True)
    items = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    raw_total = serializers.IntegerField(read_only=True)
    order_items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)

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
            "raw_total",
            "shipping_cost",
            "shipping_method",
            "tracking_code",
            "discount_amount",
            "coupon_code",
            "customer_notes",
            "total",
            "status",
            "payment",
            "order_items",
            "status_history",
        ]
        read_only_fields = [
            "id",
            "items",
            "raw_total",
            "total",
            "order_items",
            "status_history",
        ]

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
        fields = [
            "id",
            "title",
            "recipient_name",
            "recipient_phone",
            "province",
            "city",
            "address",
            "postal_code",
            "unit",
            "is_default",
        ]
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
    variant_id = serializers.IntegerField(source="variant.id", read_only=True, allow_null=True)
    variant_title = serializers.CharField(source="variant.title", read_only=True, allow_null=True)
    price = serializers.IntegerField(source="unit_price", read_only=True)
    subtotal = serializers.IntegerField(read_only=True)
    stock = serializers.IntegerField(source="product.stock", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "variant_id",
            "variant_title",
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
        return request.build_absolute_uri(url) if request else url


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "total_items", "total_price", "items"]


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "min_purchase_amount",
            "valid_from",
            "valid_until",
            "is_active",
        ]
        read_only_fields = ["id"]


class PaymentTransactionSerializer(serializers.ModelSerializer):
    order_code = serializers.CharField(source="order.code", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "order_code",
            "amount",
            "gateway",
            "authority",
            "ref_id",
            "card_pan",
            "status",
            "created_at",
            "verified_at",
        ]
        read_only_fields = ["id", "authority", "ref_id", "status", "created_at", "verified_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "link",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BannerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = [
            "id",
            "title",
            "subtitle",
            "image",
            "link_url",
            "banner_type",
            "display_order",
            "is_active",
        ]

    def get_image(self, obj: Banner) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "phone", "email", "subject", "message", "created_at"]
        read_only_fields = ["id", "created_at"]


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ["id", "email_or_phone", "created_at"]
        read_only_fields = ["id", "created_at"]


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = [
            "title",
            "description",
            "phone_support",
            "email_support",
            "address",
            "instagram_url",
            "telegram_url",
            "whatsapp_number",
            "free_shipping_threshold",
            "default_shipping_cost",
            "vat_percent",
        ]


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
                video=uploaded,
                original_name=uploaded.name,
            )


class ProfileSerializer(serializers.Serializer):
    NameAndFamily = serializers.CharField(max_length=255, required=False, allow_blank=True)
    BirthDate = serializers.CharField(max_length=30, required=False, allow_blank=True)
    IdCard = serializers.CharField(max_length=30, required=False, allow_blank=True)
    Email = serializers.EmailField(required=False, allow_blank=True)
    Number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
