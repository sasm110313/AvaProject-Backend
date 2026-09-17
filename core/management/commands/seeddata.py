from django.core.management.base import BaseCommand

from core.models import Article, Order, OrderItem, Product, User

PRODUCTS = [
    {"name": "اسپیکر مانیتورینگ استودیویی JBL 305P", "category": "اسپیکر", "sku": "SPK-1001", "price": 12500000, "stock": 14, "threshold": 5},
    {"name": "هدفون استودیویی Audio-Technica ATH-M50x", "category": "هدفون", "sku": "HDP-2044", "price": 8900000, "stock": 27, "threshold": 8},
    {"name": "آمپلی‌فایر لوله‌ای Marshall DSL40CR", "category": "آمپلی‌فایر", "sku": "AMP-3312", "price": 34200000, "stock": 3, "threshold": 4},
    {"name": "میکروفون کاندنسر Shure SM7B", "category": "میکروفون", "sku": "MIC-4090", "price": 21800000, "stock": 9, "threshold": 5},
    {"name": "میکسر دیجیتال Behringer X32", "category": "میکسر", "sku": "MIX-5501", "price": 58900000, "stock": 2, "threshold": 3},
    {"name": "کابل بالانس XLR سه‌متری", "category": "کابل و اتصالات", "sku": "CBL-6002", "price": 450000, "stock": 120, "threshold": 20},
    {"name": "اسپیکر پرتابل JBL Charge 5", "category": "اسپیکر", "sku": "SPK-1002", "price": 9800000, "stock": 0, "threshold": 6},
    {"name": "هدفون بی‌سیم Sony WH-1000XM5", "category": "هدفون", "sku": "HDP-2045", "price": 15600000, "stock": 18, "threshold": 8},
    {"name": "میکروفون یقه‌ای بی‌سیم Rode Wireless GO II", "category": "میکروفون", "sku": "MIC-4091", "price": 13400000, "stock": 6, "threshold": 5},
    {"name": "آمپلی‌فایر هدفون FiiO K7", "category": "آمپلی‌فایر", "sku": "AMP-3313", "price": 6700000, "stock": 11, "threshold": 5},
    {"name": "میکسر رومیزی Yamaha MG10XU", "category": "میکسر", "sku": "MIX-5502", "price": 17300000, "stock": 5, "threshold": 3},
    {"name": "کابل TRS به TRS استریو", "category": "کابل و اتصالات", "sku": "CBL-6003", "price": 320000, "stock": 85, "threshold": 20},
    {"name": "اسپیکر بلوتوثی Marshall Emberton II", "category": "اسپیکر", "sku": "SPK-1003", "price": 7200000, "stock": 22, "threshold": 8},
    {"name": "هدفون گیمینگ HyperX Cloud III", "category": "هدفون", "sku": "HDP-2046", "price": 5400000, "stock": 4, "threshold": 6},
    {"name": "میکروفون USB Blue Yeti", "category": "میکروفون", "sku": "MIC-4092", "price": 8100000, "stock": 16, "threshold": 6},
]

CUSTOMERS = [
    {"name": "علی محمدی", "phone": "09121111111", "email": "ali.m@example.com"},
    {"name": "سارا احمدی", "phone": "09352222222", "email": "sara.a@example.com"},
    {"name": "رضا کریمی", "phone": "09193333333", "email": "reza.k@example.com"},
    {"name": "مریم حسینی", "phone": "09214444444", "email": "maryam.h@example.com"},
    {"name": "امیر رضایی", "phone": "09385555555", "email": "amir.r@example.com"},
    {"name": "نگار صادقی", "phone": "09016666666", "email": "negar.s@example.com"},
    {"name": "حسین یزدانی", "phone": "09337777777", "email": "hossein.y@example.com"},
    {"name": "زهرا نوری", "phone": "09128888888", "email": "zahra.n@example.com"},
]

ORDERS = [
    {"code": "ORD-9001", "customer": "علی محمدی", "phone": "09121111111", "date": "1404/05/20", "items": 2, "total": 21400000, "status": "تحویل شده", "payment": "پرداخت شده"},
    {"code": "ORD-9002", "customer": "سارا احمدی", "phone": "09352222222", "date": "1404/05/21", "items": 1, "total": 8900000, "status": "در حال ارسال", "payment": "پرداخت شده"},
    {"code": "ORD-9003", "customer": "رضا کریمی", "phone": "09193333333", "date": "1404/05/21", "items": 3, "total": 47300000, "status": "در انتظار پردازش", "payment": "در انتظار"},
    {"code": "ORD-9004", "customer": "مریم حسینی", "phone": "09214444444", "date": "1404/05/22", "items": 1, "total": 34200000, "status": "تحویل شده", "payment": "پرداخت شده"},
    {"code": "ORD-9005", "customer": "امیر رضایی", "phone": "09385555555", "date": "1404/05/22", "items": 4, "total": 15650000, "status": "لغو شده", "payment": "بازگشت وجه"},
    {"code": "ORD-9006", "customer": "نگار صادقی", "phone": "09016666666", "date": "1404/05/23", "items": 2, "total": 13300000, "status": "در حال ارسال", "payment": "پرداخت شده"},
    {"code": "ORD-9007", "customer": "حسین یزدانی", "phone": "09337777777", "date": "1404/05/23", "items": 1, "total": 58900000, "status": "در انتظار پردازش", "payment": "در انتظار"},
    {"code": "ORD-9008", "customer": "زهرا نوری", "phone": "09128888888", "date": "1404/05/24", "items": 2, "total": 9700000, "status": "تحویل شده", "payment": "پرداخت شده"},
    {"code": "ORD-9009", "customer": "کیان مرادی", "phone": "09159999999", "date": "1404/05/24", "items": 1, "total": 6700000, "status": "در حال ارسال", "payment": "پرداخت شده"},
    {"code": "ORD-9010", "customer": "الناز جعفری", "phone": "09300000000", "date": "1404/05/25", "items": 3, "total": 22300000, "status": "در انتظار پردازش", "payment": "در انتظار"},
]

ARTICLES = [
    {
        "title": "چطور اسپیکر مانیتورینگ مناسب استودیوی خانگی انتخاب کنیم؟",
        "excerpt": "راهنمای انتخاب اسپیکر مانیتورینگ برای فضاهای کوچک و استودیوی خانگی.",
        "content": "",
        "category": "راهنمای خرید",
        "author": "تیم آوای انعکاس",
        "published_at": "1404/04/12",
        "status": "منتشر شده",
    },
    {
        "title": "مقایسه میکروفون‌های کاندنسر و دینامیک",
        "excerpt": "تفاوت‌های کاربردی این دو نوع میکروفون در ضبط صدا و پادکست.",
        "content": "",
        "category": "آموزشی",
        "author": "تیم آوای انعکاس",
        "published_at": "1404/05/02",
        "status": "پیش‌نویس",
    },
]


class Command(BaseCommand):
    help = "Seeds initial store data"

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write("Data already seeded, skipping.")
            return

        created_products = []
        for item in PRODUCTS:
            p = Product.objects.create(**item)
            created_products.append(p)
        self.stdout.write(f"Seeded {len(created_products)} products.")

        user_map = {}
        for item in CUSTOMERS:
            u, _ = User.objects.get_or_create(
                phone=item["phone"],
                defaults={"name": item["name"], "email": item["email"]},
            )
            user_map[item["name"]] = u
        self.stdout.write(f"Seeded {len(CUSTOMERS)} customers.")

        for item in ORDERS:
            linked_user = user_map.get(item["customer"])
            order = Order.objects.create(
                code=item["code"],
                user=linked_user,
                customer=item["customer"],
                phone=item["phone"],
                email=linked_user.email if linked_user else "",
                address="تهران، خیابان ولیعصر",
                date=item["date"],
                status=item["status"],
                payment=item["payment"],
            )
            base = item["total"] // item["items"]
            rem = item["total"] % item["items"]
            for i in range(item["items"]):
                matched_prod = created_products[i % len(created_products)]
                OrderItem.objects.create(
                    order=order,
                    product=matched_prod,
                    product_name=matched_prod.name,
                    price=base + (1 if i < rem else 0),
                    quantity=1,
                )
        self.stdout.write(f"Seeded {len(ORDERS)} orders.")

        for item in ARTICLES:
            Article.objects.create(**item)
        self.stdout.write(f"Seeded {len(ARTICLES)} articles.")