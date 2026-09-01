from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    sku = models.CharField(max_length=100)
    price = models.BigIntegerField()
    stock = models.IntegerField(default=0)
    threshold = models.IntegerField(default=5)
    video = models.FileField(upload_to="products/videos/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_images")
    image = models.FileField(upload_to="products/images/")
    original_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    ORDER_STATUSES = ["در انتظار پردازش", "در حال ارسال", "تحویل شده", "لغو شده"]
    PAYMENT_STATUSES = ["پرداخت شده", "در انتظار", "بازگشت وجه"]

    code = models.CharField(max_length=20, unique=True)
    customer = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    date = models.CharField(max_length=20)
    status = models.CharField(max_length=50, default=ORDER_STATUSES[0])
    payment = models.CharField(max_length=50, default=PAYMENT_STATUSES[1])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    @property
    def items(self):
        return sum(item.quantity for item in self.order_items.all())

    @property
    def total(self):
        return sum(item.price * item.quantity for item in self.order_items.all())

    def __str__(self):
        return self.code


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=255)
    price = models.BigIntegerField()
    quantity = models.IntegerField(default=1)


class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.CharField(max_length=255, blank=True)
    joined = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class Article(models.Model):
    ARTICLE_STATUSES = ["منتشر شده", "پیش‌نویس"]

    title = models.CharField(max_length=255)
    excerpt = models.TextField(blank=True)
    content = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    author = models.CharField(max_length=255, blank=True)
    published_at = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=50, default=ARTICLE_STATUSES[1])
    cover_image = models.FileField(upload_to="articles/covers/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.title


class ArticleVideo(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="article_videos")
    video = models.FileField(upload_to="articles/videos/")
    original_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OtpCode(models.Model):
    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)