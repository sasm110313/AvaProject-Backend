from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

OTP_TTL_MINUTES = 10
MAX_OTP_ATTEMPTS = 10


class UserManager(BaseUserManager):
    def create_user(self, phone: str, password: str | None = None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")
        phone = phone.strip()
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not password:
            raise ValueError("Superuser requires password")
        return self.create_user(phone=phone, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True, null=True)
    national_code = models.CharField(max_length=10, blank=True)
    birth_date = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    avatar = models.FileField(upload_to="avatars/", null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.name or self.phone

    @property
    def orders_count(self) -> int:
        return self.orders.count()

    @property
    def total_spent(self) -> int:
        return sum(order.total for order in self.orders.filter(payment="پرداخت شده"))

    @property
    def joined(self) -> str:
        from .jalali import gregorian_to_jalali
        dt = self.created_at
        jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
        return f"{jy:04d}/{jm:02d}/{jd:02d}"


class Customer(User):
    class Meta:
        proxy = True
        ordering = ["-id"]


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    title = models.CharField(max_length=100, default="خانه")
    recipient_name = models.CharField(max_length=255, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    province = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField()
    postal_code = models.CharField(max_length=20, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-id"]

    def __str__(self) -> str:
        return f"{self.title}: {self.address[:30]}"


class OtpCode(models.Model):
    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=10)
    failed_attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["phone", "created_at"]),
        ]

    def is_expired(self) -> bool:
        return (timezone.now() - self.created_at).total_seconds() > OTP_TTL_MINUTES * 60


class SmsLog(models.Model):
    STATUS_CHOICES = (
        ("sent", "ارسال شده"),
        ("failed", "خطا در ارسال"),
        ("simulated", "شبیه‌سازی شده"),
    )

    phone = models.CharField(max_length=20, db_index=True)
    message = models.TextField()
    template = models.CharField(max_length=100, blank=True)
    provider = models.CharField(max_length=50, default="console")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="simulated", db_index=True)
    provider_msg_id = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.phone} - {self.template or 'custom'} ({self.status})"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True)
    image = models.FileField(upload_to="categories/", null=True, blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True) or f"cat-{self.name}"
        super().save(*args, **kwargs)


class Product(models.Model):
    name = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    brand = models.CharField(max_length=100, blank=True, db_index=True)
    category = models.CharField(max_length=100, db_index=True)
    category_rel = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    price = models.BigIntegerField(validators=[MinValueValidator(1)])
    old_price = models.BigIntegerField(null=True, blank=True)
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    threshold = models.IntegerField(default=5, validators=[MinValueValidator(0)])
    rating = models.FloatField(default=5.0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    views_count = models.IntegerField(default=0)
    sales_count = models.IntegerField(default=0)
    weight_grams = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    video = models.FileField(upload_to="products/videos/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.name

    def delete(self, *args, **kwargs):
        for img in self.product_images.all():
            img.delete()
        if self.video:
            self.video.delete(save=False)
        super().delete(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_images")
    image = models.FileField(upload_to="products/images/")
    original_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def delete(self, *args, **kwargs):
        self.image.delete(save=False)
        super().delete(*args, **kwargs)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    title = models.CharField(max_length=255)  # e.g., "مشکی - ۲۵۰ اهم", "سفید"
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    price_override = models.BigIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.product.name} ({self.title})"

    @property
    def price(self) -> int:
        return self.price_override if self.price_override is not None else self.product.price


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews")
    user_name = models.CharField(max_length=255, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    pros = models.JSONField(default=list, blank=True)
    cons = models.JSONField(default=list, blank=True)
    is_approved = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.user_name or 'کاربر'} - {self.product.name} ({self.rating}★)"


class ProductQuestion(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="questions")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="questions")
    user_name = models.CharField(max_length=255, blank=True)
    question_text = models.TextField()
    is_approved = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.product.name}: {self.question_text[:40]}"


class ProductAnswer(models.Model):
    question = models.ForeignKey(ProductQuestion, on_delete=models.CASCADE, related_name="answers")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="answers")
    user_name = models.CharField(max_length=255, blank=True)
    answer_text = models.TextField()
    is_admin_answer = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"پاسخ به {self.question.id}: {self.answer_text[:40]}"


class Coupon(models.Model):
    DISCOUNT_TYPES = (
        ("percent", "درصدی"),
        ("fixed", "مبلغ ثابت"),
    )

    code = models.CharField(max_length=50, unique=True, db_index=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default="percent")
    discount_value = models.BigIntegerField(validators=[MinValueValidator(1)])
    max_discount_amount = models.BigIntegerField(null=True, blank=True)
    min_purchase_amount = models.BigIntegerField(default=0)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)
    per_user_limit = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == 'percent' else ' تومان'})"

    def is_valid_now(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False
        return True


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="coupon_usages")
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="coupon_usages")
    discount_applied = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="carts")
    session_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="carts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self) -> int:
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name="cart_items")
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        unique_together = ("cart", "product", "variant")

    @property
    def unit_price(self) -> int:
        if self.variant and self.variant.price_override is not None:
            return self.variant.price_override
        return self.product.price

    @property
    def subtotal(self) -> int:
        return self.unit_price * self.quantity


class Order(models.Model):
    ORDER_STATUSES = ["در انتظار پردازش", "در حال ارسال", "تحویل شده", "مرجوع شده", "لغو شده"]
    PAYMENT_STATUSES = ["پرداخت شده", "در انتظار", "بازگشت وجه", "ناموفق"]

    code = models.CharField(max_length=30, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    customer = models.CharField(max_length=255, db_index=True)
    phone = models.CharField(max_length=20, blank=True, db_index=True)
    email = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    date = models.CharField(max_length=20)
    status = models.CharField(
        max_length=50,
        choices=[(s, s) for s in ORDER_STATUSES],
        default=ORDER_STATUSES[0],
        db_index=True,
    )
    payment = models.CharField(
        max_length=50,
        choices=[(s, s) for s in PAYMENT_STATUSES],
        default=PAYMENT_STATUSES[1],
        db_index=True,
    )
    shipping_cost = models.BigIntegerField(default=0)
    shipping_method = models.CharField(max_length=100, default="پست پیشتاز")
    tracking_code = models.CharField(max_length=100, blank=True)
    discount_amount = models.BigIntegerField(default=0)
    coupon_code = models.CharField(max_length=50, blank=True)
    customer_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    @property
    def items(self) -> int:
        return sum(item.quantity for item in self.order_items.all())

    @property
    def raw_total(self) -> int:
        return sum(item.price * item.quantity for item in self.order_items.all())

    @property
    def total(self) -> int:
        return max(0, self.raw_total + self.shipping_cost - self.discount_amount)

    def __str__(self) -> str:
        return self.code


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    variant_title = models.CharField(max_length=255, blank=True)
    product_name = models.CharField(max_length=255)
    price = models.BigIntegerField(validators=[MinValueValidator(1)])
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["id"]

    @property
    def subtotal(self) -> int:
        return self.price * self.quantity


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=50, blank=True)
    to_status = models.CharField(max_length=50)
    comment = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class PaymentTransaction(models.Model):
    GATEWAYS = [
        ("mock", "درگاه پرداخت تستی"),
        ("zarinpal", "زرین‌پال"),
        ("idpay", "آیدی‌پی"),
    ]
    STATUSES = [
        ("pending", "در انتظار پرداخت"),
        ("success", "موفق"),
        ("failed", "ناموفق"),
        ("canceled", "لغو شده"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    amount = models.BigIntegerField(validators=[MinValueValidator(1)])
    gateway = models.CharField(max_length=30, choices=GATEWAYS, default="mock")
    authority = models.CharField(max_length=100, unique=True, db_index=True)
    ref_id = models.CharField(max_length=100, blank=True)
    card_pan = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=30, choices=STATUSES, default="pending", db_index=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.order.code} - {self.amount} ({self.status})"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default="order")
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.user.phone}: {self.title}"


class Banner(models.Model):
    BANNER_TYPES = (
        ("hero", "اسلایدر اصلی صفحه اول"),
        ("promo", "بنر تبلیغاتی میانی"),
        ("sidebar", "بنر کناری"),
    )

    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    image = models.FileField(upload_to="banners/")
    link_url = models.CharField(max_length=500, blank=True)
    banner_type = models.CharField(max_length=20, choices=BANNER_TYPES, default="hero")
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "-id"]

    def __str__(self) -> str:
        return f"{self.title} ({self.banner_type})"


class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    is_responded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.name}: {self.subject}"


class NewsletterSubscriber(models.Model):
    email_or_phone = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.email_or_phone


class SiteSetting(models.Model):
    title = models.CharField(max_length=255, default="فروشگاه تجهیزات صوتی آوای انعکاس")
    description = models.TextField(blank=True, default="مرجع تخصصی خرید اسپیکر، هدفون، میکروفون و تجهیزات صوتی و استودیویی")
    phone_support = models.CharField(max_length=50, default="021-66700000")
    email_support = models.EmailField(default="info@avayenekas.com")
    address = models.TextField(default="تهران، خیابان جمهوری، تقاطع حافظ، مجتمع تجاری پیروز")
    instagram_url = models.CharField(max_length=255, blank=True, default="https://instagram.com/avayenekas")
    telegram_url = models.CharField(max_length=255, blank=True, default="https://t.me/avayenekas")
    whatsapp_number = models.CharField(max_length=50, blank=True, default="09121234567")
    free_shipping_threshold = models.BigIntegerField(default=3000000)
    default_shipping_cost = models.BigIntegerField(default=45000)
    vat_percent = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class Article(models.Model):
    ARTICLE_STATUSES = ["منتشر شده", "پیش‌نویس"]

    title = models.CharField(max_length=255)
    excerpt = models.TextField(blank=True)
    content = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    author = models.CharField(max_length=255, blank=True)
    published_at = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=50,
        choices=[(s, s) for s in ARTICLE_STATUSES],
        default=ARTICLE_STATUSES[1],
    )
    cover_image = models.FileField(upload_to="articles/covers/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.title

    def delete(self, *args, **kwargs):
        for video in self.article_videos.all():
            video.delete()
        if self.cover_image:
            self.cover_image.delete(save=False)
        super().delete(*args, **kwargs)


class ArticleVideo(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="article_videos")
    video = models.FileField(upload_to="articles/videos/")
    original_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def delete(self, *args, **kwargs):
        self.video.delete(save=False)
        super().delete(*args, **kwargs)


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        unique_together = ("user", "product")

    def __str__(self) -> str:
        return f"{self.user.phone} - {self.product.name}"
