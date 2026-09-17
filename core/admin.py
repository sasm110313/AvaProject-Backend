from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    Address,
    Article,
    ArticleVideo,
    Cart,
    CartItem,
    Customer,
    Order,
    OrderItem,
    OtpCode,
    Product,
    ProductImage,
    User,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


class ArticleVideoInline(admin.TabularInline):
    model = ArticleVideo
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["phone", "name", "email", "is_staff", "is_active", "created_at"]
    list_filter = ["is_staff", "is_active"]
    search_fields = ["phone", "name", "email"]
    ordering = ["-id"]
    fieldsets = [
        (None, {"fields": ["phone", "password"]}),
        ("اطلاعات فردی", {"fields": ["name", "email", "national_code", "birth_date", "gender"]}),
        ("دسترسی‌ها", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["phone", "password"]}),
    ]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "postal_code", "is_default", "created_at"]
    search_fields = ["user__phone", "user__name", "title", "address"]


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


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "session_key", "total_items", "total_price", "updated_at"]
    inlines = [CartItemInline]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "phone", "email", "orders_count", "total_spent", "joined"]
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