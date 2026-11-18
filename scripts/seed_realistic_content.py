import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Ava.settings")
import django
django.setup()

from decimal import Decimal
from django.utils import timezone
from core.models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
    ProductReview,
    Article,
    Banner,
    Coupon,
    User,
)

print("--- شروع بارگذاری دسته‌بندی‌ها و محصولات و مقالات نمونه واقعی ---")

# 1. Categories
CATEGORIES_DATA = [
    {
        "name": "اسپیکر و باند",
        "slug": "speakers",
        "description": "انواع باندهای اکتیو، پسیو، دکوراتیو و سقفی برای تالارها، سالن‌های کنفرانس و اجرای زنده",
        "display_order": 1,
    },
    {
        "name": "میکروفون و تجهیزات بیسیم",
        "slug": "microphones",
        "description": "میکروفون‌های باسیم و بیسیم دستی، یقه ای و استودیویی از برترین برندها",
        "display_order": 2,
    },
    {
        "name": "پاورمیکسر و میکسر صدا",
        "slug": "mixers",
        "description": "میکسرهای دیجیتال و آنالوگ و پاورمیکسرهای قدرتمند صوتی",
        "display_order": 3,
    },
    {
        "name": "آمپلی‌فایر و پاور",
        "slug": "amplifiers",
        "description": "آمپلی‌فایرهای اهمی و ولتی، رک‌مونت و صنعتی",
        "display_order": 4,
    },
    {
        "name": "هدفون و مانیتورینگ",
        "slug": "headphones",
        "description": "هدفون‌های حرفه‌ای استودیویی، مانیتورینگ گوش و دی‌جی",
        "display_order": 5,
    },
    {
        "name": "تجهیزات استودیویی و پادکست",
        "slug": "studio-gear",
        "description": "کارت صدا، مانیتورینگ استودیویی، میکروفون استودیو و میدی کنترلر",
        "display_order": 6,
    },
    {
        "name": "نورپردازی و افکت صحنه",
        "slug": "stage-lighting",
        "description": "مووینگ، لیزر استیج، دستگاه دودساز و پروژکتورهای نورپردازی",
        "display_order": 7,
    },
    {
        "name": "سیستم‌های پیجینگ و صوت عمومی",
        "slug": "paging-systems",
        "description": "میکروفون کنفرانس، بلندگوی سقفی و شیپوری و سیستم‌های پیجینگ اداری",
        "display_order": 8,
    },
    {
        "name": "کابل، اتصالات و پایه‌ها",
        "slug": "cables",
        "description": "کابل میکروفون، فیش‌های کنون و بنون، پایه باند و پایه میکروفون",
        "display_order": 9,
    },
]

category_map = {}
for c_data in CATEGORIES_DATA:
    cat = Category.objects.filter(slug=c_data["slug"]).first()
    if cat:
        cat.name = c_data["name"]
        cat.description = c_data["description"]
        cat.display_order = c_data["display_order"]
        cat.is_active = True
        cat.save()
        created = False
    else:
        cat = Category.objects.create(
            name=c_data["name"],
            slug=c_data["slug"],
            description=c_data["description"],
            display_order=c_data["display_order"],
            is_active=True,
        )
        created = True
    category_map[cat.name] = cat
    print(f"دسته‌بندی: {cat.name} ({'ایجاد شد' if created else 'به‌روز شد'})")

# 2. Existing products enrichment (link category_rel, mark featured & discounts)
print("\n--- به‌روزرسانی محصولات موجود برای نمایش پرشور در اسلایدرها ---")
existing_products = Product.objects.all()

for idx, p in enumerate(existing_products):
    # Match category
    matched_cat = None
    p_name = p.name.lower()
    if any(k in p_name for k in ["باند", "اسپیکر", "بلندگو", "rcf", "اکو"]):
        matched_cat = category_map.get("اسپیکر و باند")
    elif any(k in p_name for k in ["میکروفن", "میکروفون", "shure", "بیسیم", "یقه"]):
        matched_cat = category_map.get("میکروفون و تجهیزات بیسیم")
    elif any(k in p_name for k in ["میکسر", "پاورمیکسر", "dynacord"]):
        matched_cat = category_map.get("پاورمیکسر و میکسر صدا")
    elif any(k in p_name for k in ["آمپلی", "پاور"]):
        matched_cat = category_map.get("آمپلی‌فایر و پاور")
    elif any(k in p_name for k in ["پایه", "کابل", "گلویی", "وینچ", "فیش"]):
        matched_cat = category_map.get("کابل و اتصالات و پایه‌ها")
    elif any(k in p_name for k in ["سقفی", "پیجینگ", "شیپوری", "بوق"]):
        matched_cat = category_map.get("سیستم‌های کنفرانس و پیجینگ")
    elif any(k in p_name for k in ["هدفون", "کارت صدا", "مانیتورینگ"]):
        matched_cat = category_map.get("تجهیزات استودیویی و پادکست")

    updates = []
    if matched_cat and p.category_rel_id != matched_cat.id:
        p.category_rel = matched_cat
        p.category = matched_cat.name
        updates.extend(["category_rel", "category"])

    # Give top 40 items featured status and discounts
    if idx < 45:
        if not p.is_featured:
            p.is_featured = True
            updates.append("is_featured")
        if not p.old_price or p.old_price <= p.price:
            discount_multiplier = Decimal("1.12") + Decimal(str((idx % 10) * 0.02))
            p.old_price = (p.price * discount_multiplier).quantize(Decimal("1000"))
            updates.append("old_price")
        if p.rating < 4.0:
            p.rating = Decimal("4.6") + Decimal(str((idx % 4) * 0.1))
            updates.append("rating")
        if p.sales_count < 10:
            p.sales_count = 15 + (idx * 3)
            updates.append("sales_count")

    if updates:
        p.save(update_fields=updates)

print(f"تعداد {existing_products.count()} محصول بررسی و همگام‌سازی شدند.")

# 3. New flagship realistic products
NEW_PRODUCTS = [
    {
        "name": "پاور میکسر دایناکورد Dynacord PowerMate 1000-3",
        "subtitle": "پاورمیکسر حرفه‌ای ۱۰ کانال ساخت آلمان با ۲ آمپلی‌فایر ۱۰۰۰ وات",
        "brand": "Dynacord",
        "category_name": "پاورمیکسر و میکسر صدا",
        "price": Decimal("185000000"),
        "old_price": Decimal("198000000"),
        "stock": 5,
        "rating": Decimal("5.0"),
        "sales_count": 28,
        "is_featured": True,
        "description": "پاورمیکسر دایناکورد PowerMate 1000-3 یکی از محبوب‌ترین و مطمئن‌ترین پاورمیکسرهای جهان است. مجهز به ۶ ورودی میکروفون/لاین مونو، ۴ ورودی استریو، پردازنده دوبل افکت دیجیتال با ۱۰۰ پریست استودیویی و رابط صوتی USB با کیفیت استودیویی جهت ضبط و پلی‌بک مستقیم.",
        "specifications": {
            "توان خروجی": "2x1000 وات در 4 اهم",
            "تعداد کانال": "10 کانال (6 مونو + 4 استریو)",
            "پردازنده افکت": "دو موتور افکت دیجیتال 24 بیتی مجزا",
            "اتصال کامپیوتر": "رابط صوتی USB 4in/4out با کیفیت 24bit/96kHz",
            "وزن": "14 کیلوگرم",
            "کشور سازنده": "آلمان",
        },
        "variants": [
            {"title": "تایوان گرید A با گارانتی ۱۸ ماهه شرکتی", "price_override": Decimal("185000000"), "stock": 3},
            {"title": "آلمان اصل اورجینال با گارانتی ۲۴ ماهه طلایی", "price_override": Decimal("245000000"), "stock": 2},
        ],
    },
    {
        "name": "باند اکتیو آر سی اف RCF ART 715-A MK4",
        "subtitle": "اسپیکر اکتیو حرفه‌ای 1400 وات با ووفر 15 اینچ و تکنولوژی FiRPHASE",
        "brand": "RCF",
        "category_name": "اسپیکر و باند",
        "price": Decimal("68500000"),
        "old_price": Decimal("76000000"),
        "stock": 12,
        "rating": Decimal("4.9"),
        "sales_count": 45,
        "is_featured": True,
        "description": "اسپیکر اکتیو آر سی اف مدل ART 715-A MK4 شاهکاری در دنیای صوت حرفه‌ای است. مجهز به ووفر ۱۵ اینچی قدرتمند و درایور تیوتر ۱ اینچی با دیافراگم ۱.۷۵ اینچ، صدایی فوق‌العاده شفاف، بیسی کوبنده و تفکیک صدایی بی‌نظیر برای تالارها، گروه‌های موسیقی و مجالس مذهبی به ارمغان می‌آورد.",
        "specifications": {
            "توان خروجی": "1400 وات پیک (700 وات RMS دیجیتال)",
            "سایز ووفر": "15 اینچ با سیم‌پیچ 2.5 اینچ",
            "سایز تیوتر": "1 اینچ تیتانیوم نئودیمیوم با سیم‌پیچ 1.75 اینچ",
            "حداکثر فشار صوتی (SPL)": "130 دسی‌بل",
            "پاسخ فرکانسی": "45 هرتز تا 20000 هرتز",
            "تکنولوژی پردازش": "فیلتر فاز خطی FiRPHASE",
        },
        "variants": [
            {"title": "رنگ مشکی مات", "price_override": None, "stock": 8},
            {"title": "رنگ سفید استودیویی", "price_override": Decimal("71000000"), "stock": 4},
        ],
    },
    {
        "name": "میکروفون استودیویی و پادکست شور Shure SM7B",
        "subtitle": "میکروفون داینامیک افسانه‌ای مناسب ضبط وکال، گویندگی و پادکست",
        "brand": "Shure",
        "category_name": "میکروفون و تجهیزات بیسیم",
        "price": Decimal("32400000"),
        "old_price": Decimal("36000000"),
        "stock": 8,
        "rating": Decimal("5.0"),
        "sales_count": 52,
        "is_featured": True,
        "description": "شور SM7B انتخاب شماره یک برترین پادکسترهای دنیا، استودیوهای برادکست و خوانندگان برجسته است. الگوی کاردیوئید دقیق آن صدای محیط و نویزهای اضافه را کاملاً حذف کرده و صدایی گرم، رادیویی و گیرا ثبت می‌کند.",
        "specifications": {
            "نوع میکروفون": "داینامیک (Dynamic)",
            "الگوی قطبی": "کاردیوئید (Cardioid)",
            "پاسخ فرکانسی": "50 هرتز تا 20 کیلوهرتز",
            "امپدانس خروجی": "150 اهم",
            "شیلدینگ الکترومغناطیسی": "حفاظت کامل در برابر امواج مانیتور و کامپیوتر",
        },
    },
    {
        "name": "هدفون مانیتورینگ بیرداینامیک Beyerdynamic DT 770 PRO",
        "subtitle": "هدفون استودیویی پشت بسته با تفکیک فرکانسی استثنایی و راحتی فوق‌العاده",
        "brand": "Beyerdynamic",
        "category_name": "تجهیزات استودیویی و پادکست",
        "price": Decimal("11800000"),
        "old_price": Decimal("13500000"),
        "stock": 18,
        "rating": Decimal("4.9"),
        "sales_count": 94,
        "is_featured": True,
        "description": "هدفون DT 770 PRO استاندارد مرجع مهندسان صدا و موزیسین‌ها در سراسر جهان است. ایرپدهای مخملی بسیار نرم، پاسخ فرکانسی گسترده و عایق‌بندی عالی صدا در برابر نشتی محیط، تجربه‌ای حرفه‌ای از شنیدن موسیقی را فراهم می‌سازد.",
        "specifications": {
            "نوع طراحی": "پشت بسته (Closed-Back)",
            "امپدانس": "80 اهم",
            "پاسخ فرکانسی": "5 هرتز تا 35000 هرتز",
            "نوع پد": "مخمل ضدتعریق و قابل تعویض",
            "کشور سازنده": "دست‌ساز در آلمان",
        },
        "variants": [
            {"title": "نسخه 80 اهم (مناسب اتصال به کارت صدا، پیانو و موبایل)", "price_override": Decimal("11800000"), "stock": 10},
            {"title": "نسخه 250 اهم (مخصوص میکس و مسترینگ با آمپلی‌فایر هدفون)", "price_override": Decimal("12400000"), "stock": 8},
        ],
    },
    {
        "name": "میکروفون بیسیم دو کانال دستی جاسکو JASCO 4002",
        "subtitle": "سیستم میکروفن بیسیم UHF دو دستی فلزی با برد بالا و بدون قطعی",
        "brand": "JASCO",
        "category_name": "میکروفون و تجهیزات بیسیم",
        "price": Decimal("19500000"),
        "old_price": Decimal("22000000"),
        "stock": 15,
        "rating": Decimal("4.8"),
        "sales_count": 68,
        "is_featured": True,
        "description": "میکروفون بیسیم دو دستی جاسکو ۴۰۰۲ دارای دو فرستنده دستی با بدنه آلومینیومی مستحکم و رسیور رک‌مونت دو آنتن است. با استفاده از فناوری True Diversity و باند فرکانسی UHF، ارتباطی پایدار تا مسافت ۱۰۰ متر را بدون هیچ‌گونه افت کیفیت تضمین می‌کند.",
        "specifications": {
            "باند فرکانسی": "UHF با قابلیت تنظیم فرکانس‌های متعدد",
            "برد مفید": "۸۰ تا ۱۲۰ متر در فضای باز",
            "خروجی صوتی": "دو خروجی بالانس XLR مستقل + یک خروجی میکس TS",
            "منبع تغذیه دسته": "دو باتری 1.5 ولت قلمی AA",
        },
    },
    {
        "name": "اکو همراه پرتابل ۱۲ اینچ برین صوت مدل Barin 12150",
        "subtitle": "باند پرتابل شارژی قدرتمند همراه با میکروفون بیسیم، بلوتوث و ضبط صدا",
        "brand": "Barin Sout",
        "category_name": "اسپیکر و باند",
        "price": Decimal("14200000"),
        "old_price": Decimal("15800000"),
        "stock": 14,
        "rating": Decimal("4.7"),
        "sales_count": 58,
        "is_featured": True,
        "description": "اکو همراه ۱۲ اینچ برین صوت انتخابی فوق‌العاده برای مراسم خیابانی، کاروان‌های زیارتی، مدارس و سخنرانی در فضای باز است. مجهز به باتری داخلی پرقدرت، ورودی‌های متعدد و اکوی دو ولومه تکرار و تاخیر برای صدایی دلنشین.",
        "specifications": {
            "سایز بلندگو": "12 اینچ فول‌رنج",
            "باتری": "اتمی قابل شارژ با ماندگاری تا ۶ ساعت کار مداوم",
            "امکانات جانبی": "بلوتوث، پورت USB، شیار کارت حافظه، رادیو و ورودی AUX",
            "اقلام همراه": "میکروفون بیسیم دستی، ریموت کنترل و کاور برزنتی ضدآب",
        },
    },
    {
        "name": "کارت صدا استودیویی Focusrite Scarlett 2i2 4th Gen",
        "subtitle": "نسل چهارم محبوب‌ترین کارت صدای استودیویی با پری‌امپ‌های شفاف 69dB",
        "brand": "Focusrite",
        "category_name": "تجهیزات استودیویی و پادکست",
        "price": Decimal("16900000"),
        "old_price": Decimal("18500000"),
        "stock": 11,
        "rating": Decimal("4.9"),
        "sales_count": 41,
        "is_featured": True,
        "description": "کارت صدای فوکوسرایت Scarlett 2i2 نسل ۴ مجهز به کانورترهای سری پرچمدار RedNet با محدوده دینامیکی شگفت‌انگیز ۱۲۰ دسی‌بل، قابلیت تنظیم خودکار گین (Auto Gain) و محافظت در برابر دیستورشن (Clip Safe) است.",
        "specifications": {
            "نرخ نمونه‌برداری": "192 کیلوهرتز / 24 بیت",
            "ورودی/خروجی": "2 ورودی کمبو میکروفون/لاین + 2 خروجی بالانس مانیتور",
            "پری‌امپ": "2 پری‌امپ نسل جدید با گین 69dB و حالت محبوب Air",
            "درگاه اتصال": "USB-C با تغذیه از کابل (Bus-Powered)",
        },
    },
    {
        "name": "پایه باند بادی وینچی SPL مدل Heavy Duty Pro",
        "subtitle": "پایه باند سنگین وینچ‌دار با حداکثر ارتفاع ۴.۲ متر و امنیت دوگانه",
        "brand": "SPL",
        "category_name": "کابل و اتصالات و پایه‌ها",
        "price": Decimal("4600000"),
        "old_price": Decimal("5200000"),
        "stock": 25,
        "rating": Decimal("4.8"),
        "sales_count": 112,
        "is_featured": True,
        "description": "پایه باند وینچی SPL برای بالا بردن آسان و ایمن سنگین‌ترین باندهای تا ۸۰ کیلوگرم طراحی شده است. به لطف سیستم وینچ نرم با سیم بکسل فولادی و پین قفل ایمنی خودکار، نصب باندهای صحنه را در کوتاه‌ترین زمان ممکن می‌سازد.",
        "specifications": {
            "حداکثر ارتفاع": "420 سانتی‌متر",
            "حداقل ارتفاع": "170 سانتی‌متر",
            "حداکثر تحمل وزن": "80 کیلوگرم",
            "جنس بدنه": "آلیاژ فولاد سنگین با رنگ الکترواستاتیک کوره ای ضدخش",
        },
    },
]

for p_idx, p_info in enumerate(NEW_PRODUCTS):
    cat = category_map.get(p_info["category_name"])
    sku_code = f"SKU-AVA-{p_idx+101}"
    prod = Product.objects.filter(name=p_info["name"]).first()
    if not prod:
        prod = Product.objects.create(
            name=p_info["name"],
            sku=sku_code,
            subtitle=p_info.get("subtitle", ""),
            brand=p_info.get("brand", ""),
            category_rel=cat,
            category=cat.name if cat else "",
            price=p_info["price"],
            old_price=p_info.get("old_price"),
            stock=p_info.get("stock", 10),
            rating=p_info.get("rating", Decimal("4.8")),
            sales_count=p_info.get("sales_count", 20),
            is_featured=p_info.get("is_featured", True),
            is_active=True,
            description=p_info.get("description", ""),
            specifications=p_info.get("specifications", {}),
        )
        created = True
    else:
        prod.subtitle = p_info.get("subtitle", prod.subtitle)
        prod.brand = p_info.get("brand", prod.brand)
        prod.category_rel = cat
        prod.category = cat.name if cat else ""
        prod.price = p_info["price"]
        prod.old_price = p_info.get("old_price")
        prod.stock = p_info.get("stock", prod.stock)
        prod.rating = p_info.get("rating", prod.rating)
        prod.sales_count = p_info.get("sales_count", prod.sales_count)
        prod.is_featured = True
        prod.is_active = True
        prod.description = p_info.get("description", prod.description)
        prod.specifications = p_info.get("specifications", prod.specifications)
        prod.save()
        created = False

    # Assign variants if defined
    if "variants" in p_info:
        for v_idx, v_data in enumerate(p_info["variants"]):
            var_sku = f"VAR-{prod.id}-{v_idx+1}"
            ProductVariant.objects.get_or_create(
                product=prod,
                title=v_data["title"],
                defaults={
                    "sku": var_sku,
                    "price_override": v_data.get("price_override"),
                    "stock": v_data.get("stock", 5),
                    "is_active": True,
                },
            )

    # Assign an image from existing product images if not present
    if not prod.product_images.exists():
        sample_img = ProductImage.objects.first()
        if sample_img:
            ProductImage.objects.create(
                product=prod,
                image=sample_img.image,
                original_name=f"{prod.name}.jpg",
            )

    print(f"محصول شاخص: {prod.name} ({'ایجاد شد' if created else 'به‌روز شد'})")


# 4. Realistic Articles (وبلاگ)
ARTICLES_DATA = [
    {
        "title": "راهنمای خرید میکروفون مناسب پادکست و وکال در سال ۱۴۰۳",
        "excerpt": "برای راه‌اندازی پادکست یا ضبط صدای حرفه‌ای، انتخاب میکروفون مناسب تفاوت میان یک اثر آماتور و خروجی استودیویی را رقم می‌زند. در این مقاله به بررسی تفاوت‌های کاندنسر و داینامیک می‌پردازیم.",
        "category": "راهنمای خرید",
        "author": "تیم فنی آوای انعکاس",
        "content": """
### میکروفون داینامیک یا کاندنسر؛ کدام برای شما مناسب است؟

یکی از متداول‌ترین پرسش‌های علاقه‌مندان به ضبط صدا و پادکست، انتخاب میان میکروفون داینامیک و کاندنسر است:

1. **میکروفون‌های داینامیک (مانند Shure SM7B و Shure SM58):**
   - در برابر نویز محیط، انعکاس صدا و اتاق‌های آکوستیک‌نشده مقاومت بالایی دارند.
   - صدایی گرم و بیس‌دار ارائه می‌دهند و برای اتاق‌های معمولی خانه ایده‌آل هستند.

2. **میکروفون‌های کاندنسر (مانند Rode NT1):**
   - حساسیت فوق‌العاده بالا به جزئیات صدا و فرکانس‌های زیر.
   - نیازمند فانتوم پاور ۴۸ ولت و اتاقی با آکوستیک مناسب و سکوت کامل هستند.

#### نتیجه‌گیری
اگر در اتاق آکوستیک‌نشده یا منزل ضبط می‌کنید، میکروفون‌های داینامیک با پترن کاردیوئید بهترین و مطمئن‌ترین انتخاب شما خواهند بود.
        """.strip(),
    },
    {
        "title": "تفاوت باند اکتیو و پسیو؛ کدام انتخاب برای تالار و مراسم بهتر است؟",
        "excerpt": "باند اکتیو یا پسیو؟ هر کدام چه مزایا و معایبی دارند و برای تالارها، حسینیه‌ها و سالن‌های همایش کدام گزینه به صرفه‌تر و مطمئن‌تر است؟",
        "category": "آموزش و بررسی",
        "author": "مهندس علیرضا محمدی",
        "content": """
### تفاوت اصلی باند اکتیو و پسیو

- **باند اکتیو (Active):**
  آمپلی‌فایر اختصاصی داخل خود کابینت بلندگو تعبیه شده است. نیاز به پاور جداگانه ندارد و با کابل برق و یک کابل سیگنال صدا کار می‌کند.
  - **مزایا:** راه‌اندازی بسیار آسان، بهینه‌سازی دقیق آمپلی‌فایر با درایورها، وزن کمتر در جابجایی کابل‌ها.

- **باند پسیو (Passive):**
  نیاز به یک آمپلی‌فایر یا پاورمیکسر مجزا دارد تا توان لازم را از طریق کابل اسپیکون تامین کند.
  - **مزایا:** هزینه اولیه مناسب‌تر در خریدهای چندتایی، عدم نیاز به کابل‌کشی برق جداگانه به هر باند در ارتفاع.
        """.strip(),
    },
    {
        "title": "۵ اصل طلایی در راه‌اندازی و آکوستیک استودیوی خانگی (Home Studio)",
        "excerpt": "چگونه با کمترین هزینه، اتاقی با کیفیت صدای ایده‌آل برای میکس، مسترینگ و ضبط صدا بسازیم؟ بررسی جایگذاری اسپیکرهای مانیتورینگ و پنل‌های آکوستیک.",
        "category": "تجهیزات استودیویی",
        "author": "تیم فنی آوای انعکاس",
        "content": """
### اصول چیدمان و عایق‌بندی استودیو خانگی

1. **قانون مثلث متساوی‌الاضلاع:** فاصله سر شنونده تا مانیتور چپ و راست باید دقیقاً برابر باشد.
2. **پرهیز از قرار دادن اسپیکر مانیتورینگ در گوشه‌های اتاق:** برای جلوگیری از تجمع بی‌رویه فرکانس‌های باس.
3. **استفاده از بیس‌ترپ (Bass Trap) در گوشه‌ها:** جهت مهار رزونانس‌های فرکانس پایین.
4. **نصب پنل‌های جاذب در نقاط بازتاب اولیه:** روی دیوارهای طرفین میز کار.
5. **استفاده از پدهای ایزولاسیون زیر مانیتورها:** جلوگیری از انتقال ارتعاشات به سطح میز.
        """.strip(),
    },
    {
        "title": "راهنمای جامع خرید پاور میکسر برای هیئت‌ها و مساجد",
        "excerpt": "نکات اساسی در انتخاب پاور میکسر مناسب برای مجالس مذهبی و مداحی: توان موثر، تعداد خروجی‌های مستقل، کیفیت افکت پینگ‌پنگی و محافظت در برابر نوسان برق.",
        "category": "سیستم‌های صوتی مذهبی",
        "author": "کارشناس صوت آوای انعکاس",
        "content": """
### ویژگی‌های ضروری پاور میکسر برای مراسمات مذهبی

در مجالس مذهبی و مداحی، کیفیت و شفافیت افکت تکرار (Delay/Ping-Pong) و توان بالا در مداومت کار اهمیت حیاتی دارد.
- **پردازنده افکت:** وجود دو موتور مجزا برای تنظیم ریورب و تاخیر به صورت ترکیبی.
- **تعداد کانال خروجی:** توانایی درایو کردن چندین باند پسیو بدون داغ شدن بیش از حد دستگاه.
- **فیدبک فیلتر:** جهت حذف سریع سوت کشیدن میکروفون مداح در فواصل نزدیک به باندها.
        """.strip(),
    },
]

for art_data in ARTICLES_DATA:
    art, created = Article.objects.get_or_create(
        title=art_data["title"],
        defaults={
            "excerpt": art_data["excerpt"],
            "category": art_data["category"],
            "author": art_data["author"],
            "content": art_data["content"],
            "status": "published",
            "published_at": timezone.now(),
        },
    )
    if not created:
        art.excerpt = art_data["excerpt"]
        art.content = art_data["content"]
        art.category = art_data["category"]
        art.status = "published"
        art.save()
    print(f"مقاله: {art.title} ({'ایجاد شد' if created else 'به‌روز شد'})")


# 5. Coupons
COUPONS_DATA = [
    {
        "code": "WELCOME10",
        "discount_type": "percent",
        "discount_value": Decimal("10"),
        "max_discount_amount": Decimal("500000"),
        "min_purchase_amount": Decimal("1000000"),
    },
    {
        "code": "AVA2026",
        "discount_type": "fixed",
        "discount_value": Decimal("200000"),
        "min_purchase_amount": Decimal("2000000"),
    },
    {
        "code": "SPECIAL",
        "discount_type": "percent",
        "discount_value": Decimal("15"),
        "max_discount_amount": Decimal("1000000"),
        "min_purchase_amount": Decimal("3000000"),
    },
]

for c_info in COUPONS_DATA:
    c, created = Coupon.objects.get_or_create(
        code=c_info["code"],
        defaults={
            "discount_type": c_info["discount_type"],
            "discount_value": c_info["discount_value"],
            "max_discount_amount": c_info.get("max_discount_amount"),
            "min_purchase_amount": c_info.get("min_purchase_amount", Decimal("0")),
            "is_active": True,
        },
    )
    if not created:
        c.is_active = True
        c.discount_type = c_info["discount_type"]
        c.discount_value = c_info["discount_value"]
        c.save()
    print(f"کد تخفیف: {c.code} ({'ایجاد شد' if created else 'به‌روز شد'})")


# 6. Realistic Customer Reviews
REVIEWS_DATA = [
    {
        "user_name": "محمد رضایی",
        "rating": 5,
        "comment": "کیفیت صدای فوق‌العاده شفاف و پرقدرت. برای هیئت خریدیم و کاملاً جوابگوی سالن ۲۰۰ نفره بود.",
        "pros": ["قدرت خروجی عالی", "کیفیت ساخت درجه یک", "بدون هیچ نویز اضافه"],
        "cons": ["وزن نسبتاً سنگین هنگام جابجایی"],
    },
    {
        "user_name": "امیرحسین کاظمی",
        "rating": 5,
        "comment": "بهترین انتخابی بود که برای ضبط پادکست کردم. نویز محیط رو به طرز شگفت‌انگیزی حذف می‌کنه.",
        "pros": ["عایق‌بندی صدای محیط", "صدای گرم و گیرا", "بدنه تمام فلزی"],
        "cons": ["نیاز به پری‌امپ قوی یا کلاودلیفر"],
    },
    {
        "user_name": "مهدی یوسفی",
        "rating": 4,
        "comment": "از خریدم راضیم. بسته‌بندی عالی بود و در سریع‌ترین زمان ممکن به دستم رسید. پشتیبانی آوای انعکاس هم بسیار پاسخگو بودند.",
        "pros": ["ارسال سریع", "اصالت کالا", "پاسخگویی سریع پشتیبانی"],
        "cons": [],
    },
]

featured_prods = Product.objects.filter(is_featured=True)[:5]
for idx, prod in enumerate(featured_prods):
    rev_data = REVIEWS_DATA[idx % len(REVIEWS_DATA)]
    rev, created = ProductReview.objects.get_or_create(
        product=prod,
        user_name=rev_data["user_name"],
        defaults={
            "rating": rev_data["rating"],
            "comment": rev_data["comment"],
            "pros": rev_data["pros"],
            "cons": rev_data["cons"],
            "is_approved": True,
        },
    )
    if not created:
        rev.is_approved = True
        rev.save()

# 7. Flagship Product Images & Article Covers & Banners
print("\n--- انتساب تصاویر باکیفیت به محصولات شاخص، مقالات و بنرها ---")
image_mapping = {
    'پاور میکسر دایناکورد': 'products/images/flagship/dynacord-1000.webp',
    'باند اکتیو آر سی اف': 'products/images/flagship/rcf-715.webp',
    'شور Shure': 'products/images/flagship/shure-sm58.jpg',
    'جاسکو JASCO 4002': 'products/images/flagship/jasco-4002.webp',
    'برین صوت مدل Barin 12150': 'products/images/flagship/barin-12150.webp',
    'پایه باند بادی وینچی': 'products/images/flagship/winch-stand.webp',
}
for name_part, img_path in image_mapping.items():
    p = Product.objects.filter(name__icontains=name_part).first()
    if p:
        p.product_images.all().delete()
        ProductImage.objects.create(product=p, image=img_path, original_name=img_path.split('/')[-1])
        print(f"تصویر برای {p.name}: {img_path}")

article_covers = [
    ('میکروفون مناسب', 'products/images/flagship/shure-sm58.jpg'),
    ('باند اکتیو', 'products/images/flagship/rcf-715.webp'),
    ('استودیوی خانگی', 'banners/hero2.jpg'),
    ('پاور میکسر', 'products/images/flagship/dynacord-1000.webp'),
]
for title_sub, img in article_covers:
    art = Article.objects.filter(title__icontains=title_sub).first()
    if art:
        art.cover_image = img
        art.save(update_fields=['cover_image'])
        print(f"کاور مقاله {art.title}: {img}")

banners_data = [
    {'title': 'جشنواره اسپیکرهای استودیویی و اجرای زنده', 'subtitle': 'تخفیف ویژه تا ۲۰ درصد روی معتبرترین برندهای جهان', 'link_url': '/products?category=اسپیکر+و+باند', 'banner_type': 'hero', 'display_order': 1, 'image': 'banners/hero1.jpg', 'is_active': True},
    {'title': 'تجهیزات تخصصی ضبط صدا و پادکست', 'subtitle': 'شنیدن جزئی‌ترین فرکانس‌های میکس و مسترینگ', 'link_url': '/products?category=تجهیزات+استودیویی+و+پادکست', 'banner_type': 'hero', 'display_order': 2, 'image': 'banners/hero2.jpg', 'is_active': True},
    {'title': 'مشاوره و نصب سیستم‌های صوت و تصویر', 'subtitle': 'اجرای پروژه‌های سالن‌های همایش و اماکن مذهبی', 'link_url': '/contact', 'banner_type': 'hero', 'display_order': 3, 'image': 'banners/promo1.jpg', 'is_active': True},
    {'title': 'تجهیزات اجرای زنده و هیئت', 'subtitle': 'باند و اکو همراه، پاورمیکسر و میکروفن', 'link_url': '/products?category=اسپیکر+و+باند', 'banner_type': 'promo', 'display_order': 1, 'image': 'banners/hero1.jpg', 'is_active': True},
    {'title': 'تجهیزات استودیو و ضبط صدا', 'subtitle': 'کارت صدا، مانیتورینگ و میکروفون استودیویی', 'link_url': '/products?category=تجهیزات+استودیویی+و+پادکست', 'banner_type': 'promo', 'display_order': 2, 'image': 'banners/hero2.jpg', 'is_active': True},
    {'title': 'سیستم‌های پیجینگ و صوت عمومی', 'subtitle': 'بلندگوهای سقفی و شیپوری هوشمند', 'link_url': '/products?category=سیستم‌های+پیجینگ+و+صوت+عمومی', 'banner_type': 'promo', 'display_order': 3, 'image': 'banners/promo1.jpg', 'is_active': True},
]
for b_info in banners_data:
    b = Banner.objects.filter(title=b_info['title']).first()
    if not b:
        Banner.objects.create(**b_info)
    else:
        for k, v in b_info.items():
            setattr(b, k, v)
        b.save()
    print(f"بنر: {b_info['title']} ({b_info['banner_type']})")

print("\n--- تمامی اطلاعات با موفقیت در پایگاه داده ایجاد و به‌روزرسانی شدند! ---")
