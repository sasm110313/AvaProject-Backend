import json
import os

from rest_framework import serializers

from .jalali import random_name
from .models import Article, ArticleVideo, Customer, Order, Product, ProductImage


class ProductSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "category", "sku", "price", "stock", "status", "threshold", "images", "video"]
        read_only_fields = ["id", "status", "images", "video"]

    def get_status(self, obj):
        return "فعال" if obj.stock > 0 else "ناموجود"

    def get_images(self, obj):
        request = self.context.get("request")
        result = []
        for img in obj.product_images.all():
            url = img.image.url
            if request:
                url = request.build_absolute_uri(url)
            result.append({"id": img.id, "url": url, "name": img.original_name or ""})
        return result

    def get_video(self, obj):
        if not obj.video:
            return None
        url = obj.video.url
        request = self.context.get("request")
        if request:
            url = request.build_absolute_uri(url)
        return {"url": url, "name": os.path.basename(obj.video.name)}

    def _normalize(self, value):
        if "/media/" in value:
            return value.split("/media/", 1)[-1]
        return value

    def create(self, validated_data):
        product = Product.objects.create(**validated_data)
        self._handle_files(product, self.context.get("request"))
        return product

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._handle_files(instance, self.context.get("request"))
        return instance

    def _handle_files(self, product, request):
        if not request:
            return
        files = request.FILES
        try:
            keep_paths = {
                self._normalize(u)
                for u in json.loads(request.data.get("existingImageUrls", "[]") or "[]")
            }
        except ValueError:
            keep_paths = set()
        for img in product.product_images.all():
            if self._normalize(img.image.url) not in keep_paths:
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
            product.video.save(os.path.basename(random_name("products/videos", video_file.name)), video_file)
        elif not keep_video and product.video:
            product.video.delete(save=True)


class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="code", read_only=True)
    items = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "customer", "date", "items", "total", "status", "payment"]
        read_only_fields = ["id", "items", "total"]

    def get_items(self, obj):
        return obj.items

    def get_total(self, obj):
        return obj.total


class CustomerSerializer(serializers.ModelSerializer):
    orders = serializers.SerializerMethodField()
    spent = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "email", "orders", "spent", "joined"]
        read_only_fields = ["id", "orders", "spent"]

    def get_orders(self, obj):
        return Order.objects.filter(customer__iexact=obj.name).count()

    def get_spent(self, obj):
        orders = Order.objects.filter(customer__iexact=obj.name)
        return sum(order.total for order in orders)


class ArticleSerializer(serializers.ModelSerializer):
    publishedAt = serializers.CharField(source="published_at", required=False, allow_blank=True)
    coverImage = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "title", "excerpt", "content", "category", "author", "publishedAt", "status", "coverImage", "videos"]
        read_only_fields = ["id", "publishedAt", "coverImage", "videos"]

    def get_coverImage(self, obj):
        if not obj.cover_image:
            return None
        url = obj.cover_image.url
        request = self.context.get("request")
        if request:
            url = request.build_absolute_uri(url)
        return {"url": url, "name": os.path.basename(obj.cover_image.name)}

    def get_videos(self, obj):
        request = self.context.get("request")
        result = []
        for video in obj.article_videos.all():
            url = video.video.url
            if request:
                url = request.build_absolute_uri(url)
            result.append({"id": video.id, "url": url, "name": video.original_name or ""})
        return result

    def _normalize(self, value):
        if "/media/" in value:
            return value.split("/media/", 1)[-1]
        return value

    def create(self, validated_data):
        article = Article.objects.create(**validated_data)
        self._handle_files(article, self.context.get("request"))
        return article

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._handle_files(instance, self.context.get("request"))
        return instance

    def _handle_files(self, article, request):
        if not request:
            return
        files = request.FILES
        cover_file = files.get("coverImage")
        keep_cover = request.data.get("existingCoverImageUrl")
        if cover_file:
            article.cover_image.save(os.path.basename(random_name("articles/covers", cover_file.name)), cover_file)
        elif not keep_cover and article.cover_image:
            article.cover_image.delete(save=True)
        try:
            keep_paths = {
                self._normalize(u)
                for u in json.loads(request.data.get("existingVideoUrls", "[]") or "[]")
            }
        except ValueError:
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