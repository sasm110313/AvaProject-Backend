from django.core.management.base import BaseCommand

from core.models import Article, Customer, Order, OrderItem, Product

PRODUCTS = [
    {"name": "اسپیکر مانیتورینگ استودیویی JBL 305P", "category": "اسپیکر", "sku": "SPK-1001", "price": 12500000, "stock": 14, "threshold": 5},
    {"name": "هدفون استودیویی Audio-Technica ATH-M50x", "category": "هدفون", "sku": "HDP-2044", "price": 8900000, "stock": 27, "threshold": 8},
    {"name": "آمپلی\u200cفایر لوله\u200cای Marshall DSL40CR", "category": "آمپلی\u200cفایر", "sku": "AMP-3312", "price": 34200000, "stock": 3, "threshold": 4},
    {"name": "میکروفون کاندنسر Shure SM7B", "category": "میکروفون", "sku": "MIC-4090", "price": 21800000, "stock": 9, "threshold": 5},
    {"name": "میکسر دیجیتال Behringer X32", "category": "میکسر", "sku": "MIX-5501", "price": 58900000, "stock": 2, "threshold": 3},
    {"name": "کابل بالانس XLR سه\u200cمتری", "category": "کابل و اتصالات", "sku": "CBL-6002", "price": 450000, "stock": 120, "threshold": 20},
    {"name": "اسپیکر پرتابل JBL Charge 5", "category": "اسپیکر", "sku": "SPK-1002", "price": 9800000, "stock": 0, "threshold": 6},
    {"name": "هدفون بی\u200cسیم Sony WH-1000XM5", "category": "هدفون", "sku": "HDP-2045", "price": 15600000, "stock": 18, "threshold": 8},
    {"name": "میکروفون یقه\u200cای بی\u200cسیم Rode Wireless GO II", "category": "میکروفون", "sku": "MIC-4091", "price": 13400000, "stock": 6, "threshold": 5},
    {"name": "آمپلی\u200cفایر هدفون FiiO K7", "category": "آمپلی\u200cفایر", "sku": "AMP-3313", "price": 6700000, "stock": 11, "threshold": 5},
    {"name": "میکسر رومیزی Yamaha MG10XU", "category": "میکسر", "sku": "MIX-5502", "price": 17300000, "stock": 5, "threshold": 3},
    {"name": "کابل TRS به TRS استریو", "category": "کابل و اتصالات", "sku": "CBL-6003", "price": 320000, "stock": 85, "threshold": 20},
    {"name": "اسپیکر بلوتوثی Marshall Emberton II", "category": "اسپیکر", "sku": "SPK-1003", "price": 7200000, "stock": 22, "threshold": 8},
    {"name": "هدفون گیمینگ HyperX Cloud III", "category": "هدفون", "sku": "HDP-2046", "price": 5400000, "stock": 4, "threshold": 6},
    {"name": "میکروفون USB Blue Yeti", "category": "میکروفون", "sku": "MIC-4092", "price": 8100000, "stock": 16, "threshold": 6},
]

ORDERS = [
    {"code": "ORD-9001", "customer": "علی محمدی", "date": "1404/05/20", "items": 2, "total": 21400000, "status": "تحویل شده", "payment": "پرداخت شده"},
    {"code": "ORD-9002", "customer": "سارا احمدی", "date": "1404/05/21", "items": 1, "total": 8900000, "status": "در حال ارسال", "payment": "پرداخت شده"},
    {"code": "ORD-9003", "customer": "رضا کریمی", "date": "1404/05/21", "items": 3, "total": 47300000, "status": "در انتظار پردازش", "payment": "در انتظار"},
    {"code": "ORD-9004", "customer": "مریم حسینی", "date": "1404/05/22", "items": 1, "total": 34200000, "status": "تحویل شده", "payment": "پرداخت شده"},
    {"code": "ORD-9005", "customer": "امیر رضایی", "date": "1404/05/22", "items": 4, "total": 15650000, "status": "لغو شده", "payment": "بازگشت وجه"},
    {"code": "ORD-9006", "customer": "نگار صادقی", "date": "1404/05/23", "items": 2, "total": 13300000, "status": "در حال ارسال", "payment": "پرداخت شده"},
    {"code": "ORD-9007", "customer": "حسین یزدانی", "date": "1404/05/23", "items": 1, "total": 58900000, "status": "در انتظار پردازش", "payment": "در انتظار"},
    {"code": "ORD-9008", "customer": "زهرا نوری", "date": "1404/05/24", "items": 2, "total": 9700000, "status": "تحویل شده", "payment": "پرداخت شده"},
    {"code": "ORD-9009", "customer": "کیان مرادی", "date": "1404/05/24", "items": 1, "total": 6700000, "status": "در حال ارسال", "payment": "پرداخت شده"},
    {"code": "ORD-9010", "customer": "الناز جعفری", "date": "1404/05/25", "items": 3, "total": 22300000, "status": "در انتظار پردازش", "payment": "در انتظار"},
]

CUSTOMERS = [
    {"name": "علی محمدی", "phone": "0912XXXXXXX", "email": "ali.m@example.com", "joined": "1402/11/02"},
    {"name": "سارا احمدی", "phone": "0935XXXXXXX", "email": "sara.a@example.com", "joined": "1403/02/14"},
    {"name": "رضا کریمی", "phone": "0919XXXXXXX", "email": "reza.k@example.com", "joined": "1401/07/09"},
    {"name": "مریم حسینی", "phone": "0921XXXXXXX", "email": "maryam.h@example.com", "joined": "1403/09/30"},
    {"name": "امیر رضایی", "phone": "0938XXXXXXX", "email": "amir.r@example.com", "joined": "1402/04/18"},
    {"name": "نگار صادقی", "phone": "0901XXXXXXX", "email": "negar.s@example.com", "joined": "1402/12/25"},
    {"name": "حسین یزدانی", "phone": "0933XXXXXXX", "email": "hossein.y@example.com", "joined": "1404/03/11"},
    {"name": "زهرا نوری", "phone": "0912XXXXXXX", "email": "zahra.n@example.com", "joined": "1401/10/05"},
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
        "title": "مقایسه میکروفون\u200cهای کاندنسر و دینامیک",
        "excerpt": "تفاوت\u200cهای کاربردی این دو نوع میکروفون در ضبط صدا و پادکست.",
        "content": "",
        "category": "آموزشی",
        "author": "تیم آوای انعکاس",
        "published_at": "1404/05/02",
        "status": "پیش\u200cنویس",
    },
]


class Command(BaseCommand):
    help = "Seeds initial data for the store"

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write("Data already seeded, skipping.")
            return

        for item in PRODUCTS:
            Product.objects.create(**item)
        self.stdout.write(f"Seeded {len(PRODUCTS)} products.")

        for item in ORDERS:
            order = Order.objects.create(
                code=item["code"],
                customer=item["customer"],
                phone="",
                email="",
                address="",
                date=item["date"],
                status=item["status"],
                payment=item["payment"],
            )
            base = item["total"] // item["items"]
            rem = item["total"] % item["items"]
            for i in range(item["items"]):
                OrderItem.objects.create(
                    order=order,
                    product=None,
                    product_name=item["customer"],
                    price=base + (1 if i < rem else 0),
                    quantity=1,
                )
        self.stdout.write(f"Seeded {len(ORDERS)} orders.")

        for item in CUSTOMERS:
            Customer.objects.create(**item)
        self.stdout.write(f"Seeded {len(CUSTOMERS)} customers.")

        for item in ARTICLES:
            Article.objects.create(**item)
        self.stdout.write(f"Seeded {len(ARTICLES)} articles.")