from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    Address,
    Article,
    ArticleVideo,
    Banner,
    Cart,
    CartItem,
    Category,
    ContactMessage,
    Coupon,
    CouponUsage,
    Customer,
    NewsletterSubscriber,
    Notification,
    Order,
    OrderItem,
    OrderStatusHistory,
    OtpCode,
    PaymentTransaction,
    Product,
    ProductAnswer,
    ProductImage,
    ProductQuestion,
    ProductReview,
    ProductVariant,
    SiteSetting,
    SmsLog,
    User,
)

admin.site.site_header = "پنل مدیریت فروشگاه آوای انعکاس"
admin.site.site_title = "آوای انعکاس"
admin.site.index_title = "میز کار مدیریت فروشگاه"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class ProductReviewInline(admin.TabularInline):
    model = ProductReview
    extra = 0
    fields = ["user_name", "rating", "comment", "is_approved", "created_at"]
    readonly_fields = ["created_at"]


class ProductAnswerInline(admin.TabularInline):
    model = ProductAnswer
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["created_at"]


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
        ("اطلاعات فردی", {"fields": ["name", "email", "national_code", "birth_date", "gender", "avatar"]}),
        ("دسترسی‌ها", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["phone", "password"]}),
    ]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "province", "city", "postal_code", "is_default", "created_at"]
    search_fields = ["user__phone", "user__name", "title", "address", "city"]
    list_filter = ["is_default", "province"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug", "parent", "display_order", "is_active"]
    list_editable = ["display_order", "is_active"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category", "brand", "price", "stock", "sales_count", "rating", "is_featured", "is_active"]
    list_editable = ["price", "stock", "is_featured", "is_active"]
    list_filter = ["is_active", "is_featured", "category", "brand"]
    search_fields = ["name", "sku", "brand", "description"]
    inlines = [ProductImageInline, ProductVariantInline, ProductReviewInline]
    actions = ["make_active", "make_inactive", "mark_featured"]

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = "فعال‌سازی کالاهای انتخاب‌شده"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = "غیرفعال‌سازی کالاهای انتخاب‌شده"

    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_featured.short_description = "نشانه‌گذاری به عنوان محصول ویژه"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "title", "sku", "price", "stock", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["product__name", "title", "sku"]


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "user_name", "rating", "is_approved", "created_at"]
    list_filter = ["rating", "is_approved", "created_at"]
    search_fields = ["product__name", "user_name", "comment"]
    actions = ["approve_reviews"]

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "تأیید نظرات انتخاب‌شده"


@admin.register(ProductQuestion)
class ProductQuestionAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "user_name", "is_approved", "created_at"]
    list_filter = ["is_approved", "created_at"]
    search_fields = ["product__name", "user_name", "question_text"]
    inlines = [ProductAnswerInline]
    actions = ["approve_questions"]

    def approve_questions(self, request, queryset):
        queryset.update(is_approved=True)
    approve_questions.short_description = "تأیید پرسش‌های انتخاب‌شده"


@admin.register(ProductAnswer)
class ProductAnswerAdmin(admin.ModelAdmin):
    list_display = ["id", "question", "user_name", "is_admin_answer", "is_approved", "created_at"]
    list_filter = ["is_admin_answer", "is_approved", "created_at"]
    search_fields = ["user_name", "answer_text"]
    actions = ["approve_answers"]

    def approve_answers(self, request, queryset):
        queryset.update(is_approved=True)
    approve_answers.short_description = "تأیید پاسخ‌های انتخاب‌شده"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "banner_type", "display_order", "is_active", "created_at"]
    list_editable = ["display_order", "is_active"]
    list_filter = ["banner_type", "is_active"]
    search_fields = ["title", "subtitle", "link_url"]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_type", "discount_value", "used_count", "usage_limit", "valid_until", "is_active"]
    list_filter = ["is_active", "discount_type"]
    search_fields = ["code"]


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ["coupon", "user", "order", "discount_applied", "created_at"]
    search_fields = ["coupon__code", "user__phone", "order__code"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["code", "customer", "phone", "date", "status", "payment", "raw_total", "total", "tracking_code"]
    list_filter = ["status", "payment", "shipping_method"]
    search_fields = ["code", "customer", "phone", "email", "tracking_code"]
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    actions = ["mark_processing", "mark_sent", "mark_delivered", "mark_paid"]

    def mark_processing(self, request, queryset):
        queryset.update(status="در انتظار پردازش")
    mark_processing.short_description = "تغییر وضعیت به در انتظار پردازش"

    def mark_sent(self, request, queryset):
        queryset.update(status="ارسال شده")
    mark_sent.short_description = "تغییر وضعیت به ارسال شده"

    def mark_delivered(self, request, queryset):
        queryset.update(status="تحویل داده شده")
    mark_delivered.short_description = "تغییر وضعیت به تحویل داده شده"

    def mark_paid(self, request, queryset):
        queryset.update(payment="پرداخت شده")
    mark_paid.short_description = "تغییر وضعیت به پرداخت شده"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product_name", "variant_title", "price", "quantity"]
    search_fields = ["order__code", "product_name"]


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["order", "from_status", "to_status", "comment", "created_at"]
    search_fields = ["order__code", "comment"]


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ["order", "amount", "gateway", "authority", "ref_id", "status", "created_at"]
    list_filter = ["status", "gateway"]
    search_fields = ["order__code", "authority", "ref_id"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "notification_type", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read"]
    search_fields = ["user__phone", "title", "message"]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "email", "subject", "is_responded", "created_at"]
    list_editable = ["is_responded"]
    list_filter = ["is_responded", "created_at"]
    search_fields = ["name", "phone", "email", "subject", "message"]
    actions = ["mark_as_responded"]

    def mark_as_responded(self, request, queryset):
        queryset.update(is_responded=True)
    mark_as_responded.short_description = "علامت‌گذاری به عنوان پاسخ‌داده‌شده"


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ["email_or_phone", "is_active", "created_at"]
    search_fields = ["email_or_phone"]


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ["title", "phone_support", "email_support", "free_shipping_threshold", "updated_at"]


@admin.register(SmsLog)
class SmsLogAdmin(admin.ModelAdmin):
    list_display = ["id", "phone", "template", "provider", "status", "provider_msg_id", "created_at"]
    list_filter = ["status", "provider", "template", "created_at"]
    search_fields = ["phone", "message", "provider_msg_id"]
    readonly_fields = [
        "phone",
        "message",
        "template",
        "provider",
        "status",
        "provider_msg_id",
        "error_message",
        "created_at",
    ]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "session_key", "total_items", "total_price", "coupon", "updated_at"]
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
    list_display = ["phone", "code", "failed_attempts", "created_at"]
