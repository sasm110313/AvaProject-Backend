from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Article,
    Category,
    Coupon,
    Notification,
    Order,
    OrderItem,
    OrderStatusHistory,
    Product,
    Banner,
    ProductAnswer,
    ProductQuestion,
    ProductReview,
    ProductVariant,
    SiteSetting,
    User,
)

CATEGORIES_DATA = [
    {"name": "اسپیکر", "slug": "speakers", "description": "انواع اسپیکرهای خانگی، پرتابل و مانیتورینگ استودیویی"},
    {"name": "هدفون", "slug": "headphones", "description": "هدفون‌های حرفه‌ای مانیتورینگ، بی‌سیم و گیمینگ"},
    {"name": "آمپلی‌فایر", "slug": "amplifiers", "description": "آمپلی‌فایرهای گیتار، استودیویی و هدفون"},
    {"name": "میکروفون", "slug": "microphones", "description": "میکروفون‌های کاندنسر، داینامیک و بی‌سیم"},
    {"name": "میکسر", "slug": "mixers", "description": "میکسرهای دیجیتال و آنالوگ اجرای زنده و استودیو"},
    {"name": "کابل و اتصالات", "slug": "cables", "description": "کابل‌های استاندارد XLR، TRS و تبدیل‌های صوتی"},
]

PRODUCTS_DATA = [
    {
        "name": "اسپیکر مانیتورینگ استودیویی JBL 305P",
        "category": "اسپیکر",
        "brand": "JBL",
        "sku": "SPK-1001",
        "price": 12500000,
        "old_price": 14000000,
        "stock": 14,
        "threshold": 5,
        "rating": 4.8,
        "is_featured": True,
        "description": "اسپیکر مانیتورینگ اکتیو ۵ اینچ سری ۳ با فناوری Waveguide تصویربرداری با وضوح بالا، مناسب تنظیم، میکس و مسترینگ استودیویی.",
        "specifications": {
            "توان خروجی": "۸۲ وات کلاس D",
            "سایز ووفر": "۵ اینچ",
            "سایز توییتر": "۱ اینچ نئودیمیوم",
            "پاسخ فرکانسی": "۴۳ هرتز تا ۲۴ کیلوهرتز",
            "ورودی‌ها": "XLR و 1/4 اینچ TRS بالانس",
            "وزن": "۴.۷۳ کیلوگرم",
        },
    },
    {
        "name": "هدفون استودیویی Audio-Technica ATH-M50x",
        "category": "هدفون",
        "brand": "Audio-Technica",
        "sku": "HDP-2044",
        "price": 8900000,
        "old_price": 9800000,
        "stock": 27,
        "threshold": 8,
        "rating": 4.9,
        "is_featured": True,
        "description": "معروف‌ترین و پرفروش‌ترین هدفون مانیتورینگ پشت‌بسته جهان با درایورهای اختصاصی ۴۵ میلی‌متری و بازتولید صدای فوق‌العاده دقیق.",
        "specifications": {
            "نوع درایور": "۴۵ میلی‌متر با آهنربای نئودیمیوم",
            "پاسخ فرکانسی": "۱۵ هرتز تا ۲۸ کیلوهرتز",
            "امپدانس": "۳۸ اهم",
            "حساسیت": "۹۹ دسی‌بل",
            "طراحی": "پشت بسته (Closed-back) چرخشی ۹۰ درجه",
            "وزن": "۲۸۵ گرم",
        },
    },
    {
        "name": "آمپلی‌فایر لوله‌ای Marshall DSL40CR",
        "category": "آمپلی‌فایر",
        "brand": "Marshall",
        "sku": "AMP-3312",
        "price": 34200000,
        "old_price": None,
        "stock": 3,
        "threshold": 4,
        "rating": 5.0,
        "is_featured": True,
        "description": "کمبو امپ تمام لوله‌ای ۴۰ وات با اسپیکر ۱۲ اینچ Celestion V-Type برای لحن کلاسیک راک و متال انگلیسی.",
        "specifications": {
            "توان خروجی": "۴۰ وات (قابل کاهش به ۲۰ وات)",
            "اسپیکر": "۱۲ اینچ Celestion V-Type",
            "لامپ‌های پری‌امپ": "۴ عدد ECC83",
            "لامپ‌های پاور": "۲ عدد EL34",
            "کانال‌ها": "۲ کانال (Classic Gain و Ultra Gain)",
        },
    },
    {
        "name": "میکروفون کاندنسر Shure SM7B",
        "category": "میکروفون",
        "brand": "Shure",
        "sku": "MIC-4090",
        "price": 21800000,
        "old_price": 24000000,
        "stock": 9,
        "threshold": 5,
        "rating": 5.0,
        "is_featured": True,
        "description": "استاندارد صنعت پادکست، وکال و برودکست در سراسر دنیا با الگوی قطبی کاردیوئید یکنواخت و شیلد الکترومغناطیسی قوی.",
        "specifications": {
            "نوع میکروفون": "داینامیک",
            "الگوی قطبی": "کاردیوئید",
            "پاسخ فرکانسی": "۵۰ هرتز تا ۲۰ کیلوهرتز",
            "امپدانس خروجی": "۱۵۰ اهم",
            "اتصال": "XLR سه پین",
        },
    },
    {
        "name": "میکسر دیجیتال Behringer X32",
        "category": "میکسر",
        "brand": "Behringer",
        "sku": "MIX-5501",
        "price": 58900000,
        "old_price": None,
        "stock": 2,
        "threshold": 3,
        "rating": 4.7,
        "is_featured": True,
        "description": "میکسر دیجیتال ۴۰ کاناله با ۳۲ پری‌امپ طراحی شده توسط مایداس و فیدرهای موتوری ۱۰۰ میلی‌متری.",
        "specifications": {
            "تعداد کانال‌ها": "۴۰ کانال ورودی",
            "پری‌امپ‌ها": "۳۲ ورودی میکروفون MIDAS",
            "خروجی‌ها": "۱۶ خروجی بالانس XLR",
            "رابط صوتی": "USB 2.0 با ۳۲ در ۳۲ کانال",
        },
    },
    {
        "name": "کابل بالانس XLR سه‌متری",
        "category": "کابل و اتصالات",
        "brand": "Neutrik",
        "sku": "CBL-6002",
        "price": 450000,
        "old_price": 500000,
        "stock": 120,
        "threshold": 20,
        "rating": 4.6,
        "is_featured": False,
        "description": "کابل میکروفون و اتصال مانیتورینگ ۳ متری تمام مس بدون اکسیژن (OFC) با فیش‌های نوت ریک اصل.",
        "specifications": {
            "طول کابل": "۳ متر",
            "جنس مغزی": "مس بدون اکسیژن (OFC)",
            "نوع کانکتور": "XLR مادگی به XLR نری",
        },
    },
    {
        "name": "اسپیکر پرتابل JBL Charge 5",
        "category": "اسپیکر",
        "brand": "JBL",
        "sku": "SPK-1002",
        "price": 9800000,
        "old_price": None,
        "stock": 0,
        "threshold": 6,
        "rating": 4.5,
        "is_featured": False,
        "description": "اسپیکر ضدآب و ضدغبار با باتری قدرتمند با ۲۰ ساعت شارژدهی و قابلیت پاوربانک داخلی.",
        "specifications": {
            "توان خروجی": "۴۰ وات RMS",
            "استاندارد مقاومت": "IP67 ضد آب و گرد و غبار",
            "باتری": "۷۵۰۰ میلی‌آمپر ساعت (تا ۲۰ ساعت پخش)",
        },
    },
    {
        "name": "هدفون بی‌سیم Sony WH-1000XM5",
        "category": "هدفون",
        "brand": "Sony",
        "sku": "HDP-2045",
        "price": 15600000,
        "old_price": 17200000,
        "stock": 18,
        "threshold": 8,
        "rating": 4.9,
        "is_featured": True,
        "description": "پیشرفته‌ترین سیستم حذف نویز اکتیو (ANC) در دنیا با پردازنده V1 و باتری ۳۰ ساعته همراه با شارژ سریع.",
        "specifications": {
            "پردازنده حذف نویز": "QN1 همراه با پردازنده مجتمع V1",
            "عمر باتری": "۳۰ ساعت با ANC روشن",
            "کدک‌های بلوتوث": "LDAC, AAC, SBC",
            "وزن": "۲۵۰ گرم",
        },
    },
    {
        "name": "میکروفون یقه‌ای بی‌سیم Rode Wireless GO II",
        "category": "میکروفون",
        "brand": "Rode",
        "sku": "MIC-4091",
        "price": 13400000,
        "old_price": None,
        "stock": 6,
        "threshold": 5,
        "rating": 4.8,
        "is_featured": False,
        "description": "سیستم میکروفون بی‌سیم دو کاناله اولترا کامپکت با برد ۲۰۰ متر و ضبط صدای آن‌بورد داخلی تا ۴۰ ساعت.",
        "specifications": {
            "سیستم انتقال": "دیجیتال ۲.۴ گیگاهرتز سری IV با رمزگذاری ۱۲۸ بیتی",
            "برد کاری": "تا ۲۰۰ متر در خط دید مستقیم",
            "باتری": "لیتیوم داخلی با ۷ ساعت دوام",
        },
    },
    {
        "name": "آمپلی‌فایر هدفون FiiO K7",
        "category": "آمپلی‌فایر",
        "brand": "FiiO",
        "sku": "AMP-3313",
        "price": 6700000,
        "old_price": 7500000,
        "stock": 11,
        "threshold": 5,
        "rating": 4.7,
        "is_featured": False,
        "description": "داک و آمپلی‌فایر هدفون دسکتاپ با مدار تمام بالانس THX AAA 788+ و چیپست دوگانه AK4493SEQ.",
        "specifications": {
            "چیپ DAC": "دو عدد AKM AK4493S",
            "مدار آمپلی‌فایر": "دوگانه THX AAA 788+",
            "توان خروجی بالانس": "۲۰۰۰ میلی‌وات روی ۳۲ اهم",
        },
    },
    {
        "name": "میکسر رومیزی Yamaha MG10XU",
        "category": "میکسر",
        "brand": "Yamaha",
        "sku": "MIX-5502",
        "price": 17300000,
        "old_price": 18900000,
        "stock": 5,
        "threshold": 3,
        "rating": 4.8,
        "is_featured": True,
        "description": "میکسر ۱۰ کاناله آنالوگ با پری‌امپ‌های گسسته کلاس A نوع D-PRE، پردازنده افکت SPX و رابط صوتی USB.",
        "specifications": {
            "تعداد ورودی‌ها": "۱۰ کانال (۴ مونو + ۳ استریو)",
            "پردازنده افکت": "۲۴ افکت دیجیتال حرفه‌ای الگوریتم SPX",
            "رابط USB": "۲۴ بیت / ۱۹۲ کیلوهرتز",
        },
    },
    {
        "name": "کابل TRS به TRS استریو",
        "category": "کابل و اتصالات",
        "brand": "Mogami",
        "sku": "CBL-6003",
        "price": 320000,
        "old_price": None,
        "stock": 85,
        "threshold": 20,
        "rating": 4.5,
        "is_featured": False,
        "description": "کابل اتصال بالانس پچ کورد ۱/۴ اینچی جک استریو مناسب اتصال تجهیزات رک و مانیتور به کارت صدا.",
        "specifications": {
            "طول کابل": "۱.۵ متر",
            "اتصال": "6.35mm Stereo TRS to TRS",
        },
    },
    {
        "name": "اسپیکر بلوتوثی Marshall Emberton II",
        "category": "اسپیکر",
        "brand": "Marshall",
        "sku": "SPK-1003",
        "price": 7200000,
        "old_price": 8100000,
        "stock": 22,
        "threshold": 8,
        "rating": 4.9,
        "is_featured": True,
        "description": "اسپیکر پرتابل با ظاهر نمادین آمپ‌های مارشال، صدای ۳۶۰ درجه True Stereophonic و ۳۰ ساعت شارژدهی.",
        "specifications": {
            "عمر باتری": "بیش از ۳۰ ساعت",
            "استاندارد ضد آب": "IP67",
            "بلوتوث": "نسخه ۵.۱",
        },
    },
    {
        "name": "هدفون گیمینگ HyperX Cloud III",
        "category": "هدفون",
        "brand": "HyperX",
        "sku": "HDP-2046",
        "price": 5400000,
        "old_price": 6000000,
        "stock": 4,
        "threshold": 6,
        "rating": 4.6,
        "is_featured": False,
        "description": "هدفون گیمینگ ارگونومیک با فوم حافظه‌دار باکیفیت بالا، درایورهای زاویه‌دار ۵۳ میلی‌متری و صدای فضایی DTS.",
        "specifications": {
            "درایور": "۵۳ میلی‌متری دینامیک",
            "میکروفون": "۱۰ میلی‌متری نویزکنسلینگ با فیلتر داخلی",
            "پشتیبانی صدا": "DTS Headphone:X Spatial Audio",
        },
    },
    {
        "name": "میکروفون USB Blue Yeti",
        "category": "میکروفون",
        "brand": "Logitech",
        "sku": "MIC-4092",
        "price": 8100000,
        "old_price": None,
        "stock": 16,
        "threshold": 6,
        "rating": 4.7,
        "is_featured": False,
        "description": "محبوب‌ترین میکروفون USB جهان برای استریمرها و یوتیوبرها با چهار الگوی ضبط مختلف و اتصال Plug and Play.",
        "specifications": {
            "کپسول‌ها": "۳ کپسول کاندنسر ۱۴ میلی‌متری اختصاری",
            "الگوهای قطبی": "کاردیوئید، دوجهته، چندجهته و استریو",
            "نرخ نمونه‌برداری": "۱۶ بیت / ۴۸ کیلوهرتز",
        },
    },
]

CUSTOMERS_DATA = [
    {"name": "علی محمدی", "phone": "09121111111", "email": "ali.m@example.com", "national_code": "0012345678", "city": "تهران"},
    {"name": "سارا احمدی", "phone": "09352222222", "email": "sara.a@example.com", "national_code": "0023456789", "city": "اصفهان"},
    {"name": "رضا کریمی", "phone": "09193333333", "email": "reza.k@example.com", "national_code": "0034567890", "city": "شیراز"},
    {"name": "مریم حسینی", "phone": "09214444444", "email": "maryam.h@example.com", "national_code": "0045678901", "city": "مشهد"},
    {"name": "امیر رضایی", "phone": "09385555555", "email": "amir.r@example.com", "national_code": "0056789012", "city": "تبریز"},
    {"name": "نگار صادقی", "phone": "09016666666", "email": "negar.s@example.com", "national_code": "0067890123", "city": "کرج"},
    {"name": "حسین یزدانی", "phone": "09337777777", "email": "hossein.y@example.com", "national_code": "0078901234", "city": "اهواز"},
    {"name": "زهرا نوری", "phone": "09128888888", "email": "zahra.n@example.com", "national_code": "0089012345", "city": "رشت"},
]

COUPONS_DATA = [
    {
        "code": "WELCOME",
        "discount_type": "percent",
        "discount_value": 10,
        "max_discount_amount": 500000,
        "min_purchase_amount": 1000000,
        "usage_limit": 500,
    },
    {
        "code": "AVA20",
        "discount_type": "percent",
        "discount_value": 20,
        "max_discount_amount": 1500000,
        "min_purchase_amount": 3000000,
        "usage_limit": 100,
    },
    {
        "code": "VIP100",
        "discount_type": "fixed",
        "discount_value": 1000000,
        "max_discount_amount": None,
        "min_purchase_amount": 5000000,
        "usage_limit": 50,
    },
]

ORDERS_DATA = [
    {"code": "ORD-9001", "customer": "علی محمدی", "phone": "09121111111", "date": "1404/05/20", "items": 2, "total": 21400000, "status": "تحویل شده", "payment": "پرداخت شده", "tracking_code": "TIP-7849102"},
    {"code": "ORD-9002", "customer": "سارا احمدی", "phone": "09352222222", "date": "1404/05/21", "items": 1, "total": 8900000, "status": "در حال ارسال", "payment": "پرداخت شده", "tracking_code": "PST-4920194"},
    {"code": "ORD-9003", "customer": "رضا کریمی", "phone": "09193333333", "date": "1404/05/21", "items": 3, "total": 47300000, "status": "در انتظار پردازش", "payment": "در انتظار", "tracking_code": ""},
    {"code": "ORD-9004", "customer": "مریم حسینی", "phone": "09214444444", "date": "1404/05/22", "items": 1, "total": 34200000, "status": "تحویل شده", "payment": "پرداخت شده", "tracking_code": "TIP-1928472"},
    {"code": "ORD-9005", "customer": "امیر رضایی", "phone": "09385555555", "date": "1404/05/22", "items": 4, "total": 15650000, "status": "لغو شده", "payment": "بازگشت وجه", "tracking_code": ""},
    {"code": "ORD-9006", "customer": "نگار صادقی", "phone": "09016666666", "date": "1404/05/23", "items": 2, "total": 13300000, "status": "در حال ارسال", "payment": "پرداخت شده", "tracking_code": "PST-8392019"},
    {"code": "ORD-9007", "customer": "حسین یزدانی", "phone": "09337777777", "date": "1404/05/23", "items": 1, "total": 58900000, "status": "در انتظار پردازش", "payment": "در انتظار", "tracking_code": ""},
    {"code": "ORD-9008", "customer": "زهرا نوری", "phone": "09128888888", "date": "1404/05/24", "items": 2, "total": 9700000, "status": "تحویل شده", "payment": "پرداخت شده", "tracking_code": "TIP-9920183"},
    {"code": "ORD-9009", "customer": "کیان مرادی", "phone": "09159999999", "date": "1404/05/24", "items": 1, "total": 6700000, "status": "در حال ارسال", "payment": "پرداخت شده", "tracking_code": "PST-1102934"},
    {"code": "ORD-9010", "customer": "الناز جعفری", "phone": "09300000000", "date": "1404/05/25", "items": 3, "total": 22300000, "status": "در انتظار پردازش", "payment": "در انتظار", "tracking_code": ""},
]

ARTICLES_DATA = [
    {
        "title": "چطور اسپیکر مانیتورینگ مناسب استودیوی خانگی انتخاب کنیم؟",
        "excerpt": "راهنمای انتخاب اسپیکر مانیتورینگ برای فضاهای کوچک و استودیوی خانگی.",
        "content": "برای استودیوهای خانگی معمولاً اسپیکرهای ۵ یا ۷ اینچ به دلیل محدودیت آکوستیک اتاق بهترین انتخاب هستند. ویژگی‌هایی چون پاسخ فرکانسی مسطح و قابلیت تنظیم اکوستیک پشت اسپیکر از نکات کلیدی هستند.",
        "category": "راهنمای خرید",
        "author": "تیم آوای انعکاس",
        "published_at": "1404/04/12",
        "status": "منتشر شده",
    },
    {
        "title": "مقایسه میکروفون‌های کاندنسر و دینامیک",
        "excerpt": "تفاوت‌های کاربردی این دو نوع میکروفون در ضبط صدا و پادکست.",
        "content": "میکروفون‌های کاندنسر حساسیت بسیار بالایی دارند و جزییات فرکانس‌های بالا را دقیق ثبت می‌کنند، اما میکروفون‌های دینامیک برای محیط‌های بدون آکوستیک یا صداهای بلند عملکرد بهتری ارائه می‌دهند.",
        "category": "آموزشی",
        "author": "تیم آوای انعکاس",
        "published_at": "1404/05/02",
        "status": "پیش‌نویس",
    },
]


class Command(BaseCommand):
    help = "Seeds comprehensive store data including categories, rich products, coupons, and orders"

    def handle(self, *args, **options):
        # 1. Categories
        cat_map = {}
        for cat_data in CATEGORIES_DATA:
            cat, _ = Category.objects.get_or_create(
                name=cat_data["name"],
                defaults=cat_data,
            )
            cat_map[cat.name] = cat
        self.stdout.write(f"✓ Seeded {len(cat_map)} categories.")

        # 2. Coupons
        for coupon_data in COUPONS_DATA:
            Coupon.objects.get_or_create(
                code=coupon_data["code"],
                defaults=coupon_data,
            )
        self.stdout.write(f"✓ Seeded {len(COUPONS_DATA)} coupons.")

        # 3. Products
        created_products = []
        for p_data in PRODUCTS_DATA:
            p_dict = dict(p_data)
            category_name = p_dict["category"]
            cat_obj = cat_map.get(category_name)
            p_dict["category_rel"] = cat_obj
            product, created = Product.objects.update_or_create(
                sku=p_dict["sku"],
                defaults=p_dict,
            )
            created_products.append(product)

            # Add sample reviews for top products
            if created or not product.reviews.exists():
                ProductReview.objects.create(
                    product=product,
                    user_name="کاربر تأیید شده",
                    rating=5,
                    comment="کیفیت ساخت و تفکیک صدای این کالا فوق‌العاده است. از خریدم کاملاً راضی هستم.",
                    pros=["صدای شفاف", "ارزش خرید بالا"],
                    cons=[],
                    is_approved=True,
                )

        self.stdout.write(f"✓ Seeded {len(created_products)} products with reviews.")

        # 4. Customers
        user_map = {}
        for item in CUSTOMERS_DATA:
            u, _ = User.objects.get_or_create(
                phone=item["phone"],
                defaults={
                    "name": item["name"],
                    "email": item["email"],
                    "national_code": item.get("national_code", ""),
                },
            )
            user_map[item["name"]] = u

            # Create default notification
            Notification.objects.get_or_create(
                user=u,
                title="به فروشگاه آوای انعکاس خوش آمدید!",
                defaults={
                    "message": f"سلام {u.name} عزیز، به فروشگاه تخصصی تجهیزات صوتی آوای انعکاس خوش آمدید. کد تخفیف WELCOME برای اولین خرید شما فعال است.",
                    "notification_type": "promo",
                },
            )

        self.stdout.write(f"✓ Seeded {len(CUSTOMERS_DATA)} customers with welcome notifications.")

        # 5. Orders
        for item in ORDERS_DATA:
            linked_user = user_map.get(item["customer"])
            order, created = Order.objects.get_or_create(
                code=item["code"],
                defaults={
                    "user": linked_user,
                    "customer": item["customer"],
                    "phone": item["phone"],
                    "email": linked_user.email if linked_user else "",
                    "address": f"تهران، میدان ونک، پلاک ۱۲",
                    "date": item["date"],
                    "status": item["status"],
                    "payment": item["payment"],
                    "tracking_code": item.get("tracking_code", ""),
                    "shipping_method": "پست پیشتاز",
                    "shipping_cost": 45000,
                },
            )
            if created:
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
                OrderStatusHistory.objects.create(
                    order=order,
                    from_status="",
                    to_status=order.status,
                    comment="سفارش اولیه ثبت شده در سیستم",
                )

        self.stdout.write(f"✓ Seeded {len(ORDERS_DATA)} orders.")

        # 6. Articles
        for item in ARTICLES_DATA:
            Article.objects.get_or_create(
                title=item["title"],
                defaults=item,
            )
        self.stdout.write(f"✓ Seeded {len(ARTICLES_DATA)} articles.")


        # 7. Site Settings
        SiteSetting.get_settings()
        self.stdout.write("✓ Seeded site settings.")

        # 8. Banners
        banners = [
            {"title": "جشنواره اسپیکرهای استودیویی", "subtitle": "تخفیف ویژه تا ۲۰٪ روی سری‌های حرفه‌ای JBL و یاماها", "image": "banners/hero1.jpg", "link_url": "/products?category=اسپیکر", "banner_type": "hero", "display_order": 1},
            {"title": "تجهیزات پادکست و وکال", "subtitle": "میکروفون‌های حرفه‌ای شور و رود با ضمانت اصالت", "image": "banners/hero2.jpg", "link_url": "/products?category=میکروفون", "banner_type": "hero", "display_order": 2},
            {"title": "هدفون‌های مانیتورینگ", "subtitle": "شنیدن جزئی‌ترین فرکانس‌های میکس و مسترینگ", "image": "banners/promo1.jpg", "link_url": "/products?category=هدفون", "banner_type": "promo", "display_order": 1},
        ]
        for b in banners:
            Banner.objects.get_or_create(title=b["title"], defaults=b)
        self.stdout.write("✓ Seeded banners.")

        # 9. Product Variants
        m50x = Product.objects.filter(sku="HDP-2044").first()
        if m50x:
            ProductVariant.objects.get_or_create(product=m50x, sku="HDP-2044-BLK", defaults={"title": "مشکی مات", "stock": 15})
            ProductVariant.objects.get_or_create(product=m50x, sku="HDP-2044-WHT", defaults={"title": "سفید صدفی", "stock": 8, "price_override": 9200000})
            ProductVariant.objects.get_or_create(product=m50x, sku="HDP-2044-GM", defaults={"title": "خاکستری متالیک", "stock": 4, "price_override": 9500000})

        # 10. Sample Questions & Answers
        jbl = Product.objects.filter(sku="SPK-1001").first()
        if jbl:
            q, _ = ProductQuestion.objects.get_or_create(
                product=jbl,
                user_name="نوید اسماعیلی",
                defaults={"question_text": "سلام، آیا کابل برق و پد ضد لرزش همراه این اسپیکر هست؟"}
            )
            ProductAnswer.objects.get_or_create(
                question=q,
                defaults={"user_name": "کارشناس آوای انعکاس", "answer_text": "سلام و درود. کابل برق و پدهای لاستیکی فابریک داخل جعبه موجود است، اما برای بهترین نتیجه توصیه می‌شود از پایه‌های ایزولاتور دسکتاپ استفاده فرمایید.", "is_admin_answer": True}
            )
        self.stdout.write("✓ Seeded product variants and questions.")

        self.stdout.write(self.style.SUCCESS("All e-commerce backend data successfully seeded!"))
