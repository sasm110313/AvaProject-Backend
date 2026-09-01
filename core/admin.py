from django.contrib import admin

from .models import Article, ArticleVideo, Customer, Order, OrderItem, OtpCode, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class ArticleVideoInline(admin.TabularInline):
    model = ArticleVideo
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category", "sku", "price", "stock", "threshold"]
    list_filter = ["category"]
    search_fields = ["name", "sku"]
    inlines = [ProductImageInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["code", "customer", "phone", "date", "status", "payment"]
    list_filter = ["status", "payment"]
    search_fields = ["code", "customer", "phone"]
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product_name", "price", "quantity"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "phone", "email", "joined"]
    search_fields = ["name", "phone", "email"]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "category", "author", "published_at", "status"]
    list_filter = ["status", "category"]
    search_fields = ["title"]
    inlines = [ArticleVideoInline]


@admin.register(ArticleVideo)
class ArticleVideoAdmin(admin.ModelAdmin):
    list_display = ["article", "video"]


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    list_display = ["phone", "code", "created_at"]