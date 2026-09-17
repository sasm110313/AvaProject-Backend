from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

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
    address = models.TextField()
    postal_code = models.CharField(max_length=20, blank=True)
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


class Product(models.Model):
    name = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=100, db_index=True)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    price = models.BigIntegerField(validators=[MinValueValidator(1)])
    old_price = models.BigIntegerField(null=True, blank=True)
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    threshold = models.IntegerField(default=5, validators=[MinValueValidator(0)])
    rating = models.FloatField(default=5.0)
    is_featured = models.BooleanField(default=False)
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


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="carts")
    session_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)
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
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        unique_together = ("cart", "product")

    @property
    def subtotal(self) -> int:
        return self.product.price * self.quantity


class Order(models.Model):
    ORDER_STATUSES = ["در انتظار پردازش", "در حال ارسال", "تحویل شده", "لغو شده"]
    PAYMENT_STATUSES = ["پرداخت شده", "در انتظار", "بازگشت وجه"]

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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    @property
    def items(self) -> int:
        return sum(item.quantity for item in self.order_items.all())

    @property
    def total(self) -> int:
        return sum(item.price * item.quantity for item in self.order_items.all())

    def __str__(self) -> str:
        return self.code


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=255)
    price = models.BigIntegerField(validators=[MinValueValidator(1)])
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["id"]

    @property
    def subtotal(self) -> int:
        return self.price * self.quantity


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