# راهنمای جامع اتصال و استفاده از API بک‌اند (ویژه توسعه‌دهنده فرانت‌اند)

این مستند راهنمای کامل، گام‌به‌گام و استاندارد اتصال پروژه‌ی فرانت‌اند (React / Vite) به بک‌اند جنگو (Django REST Framework) فروشگاه «آوای انعکاس» است. تمام مسیرها (Endpoints)، پارامترها، فرمت داده‌های ارسالی، نمونه پاسخ‌های JSON و راهنمای پیاده‌سازی صفحه به صفحه در این سند گردآوری شده‌اند.

---

## ۱. مشخصات عمومی سرور و اتصال

- **آدرس پایه API (Base URL):** `http://localhost:4000/api`
- **آدرس فایل‌های چندرسانه‌ای (عکس/ویدیو):** `http://localhost:4000/media/...`
- **تنظیمات CORS:** برای پورت‌های محلی فرانت (`http://localhost:5173` و `http://127.0.0.1:5173`) با هدرهای استاندارد، متدهای `GET, POST, PUT, PATCH, DELETE, OPTIONS` و پشتیبانی از Credentials فعال است.
- **مستندات تعاملی Swagger:** `http://localhost:4000/api/docs/`
- **مستندات تعاملی Redoc:** `http://localhost:4000/api/redoc/`
- **فایل اسکیما OpenAPI:** `http://localhost:4000/api/schema/`
- **ماژول آماده جاوااسکریپت برای فرانت‌اند:** فایل آماده `Front/AvayEnekas/src/api/shopApi.js` تمامی توابع ارتباطی را با مدیریت خودکار توکن و خطایابی فراهم کرده است.

---

## ۲. راهنمای گام‌به‌گام اتصال فرانت‌اند (Step-by-Step Integration Guide)

### قدم ۱: اجرای بک‌اند
از پوشه اصلی پروژه در ترمینال دستورات زیر را اجرا کنید:
```bash
# لینوکس / مک:
source venv/bin/activate
python manage.py runserver 4000

# ویندوز:
venv\Scripts\activate
python manage.py runserver 4000
```
سپس با مرورگر آدرس `http://localhost:4000/api/products/` را باز کنید تا از صحت عملکرد مطمئن شوید.

---

### قدم ۲: تنظیم متغیر محیطی در فرانت‌اند
در ریشه پروژه فرانت (`Front/AvayEnekas`) فایل `.env` را بسازید یا ویرایش کنید:
```env
VITE_API_BASE_URL=http://localhost:4000/api
```
در پنل ادمین (`Front/AvayEnekas/src/Components/AdminPannel/Api.jsx`) نیز متغیر زیر را مقداردهی کنید:
```javascript
export const USE_MOCK_DATA = false;
```

---

### قدم ۳: چرخه احراز هویت با شماره موبایل (OTP & JWT)

سیستم ورود بدون رمز عبور و با ارسال پیامک کد یک‌بار مصرف است:

```
[کاربر] ---> وارد کردن شماره موبایل ---> POST /api/auth/send-code/
                                            |
                                            v
                                     دریافت پیامک (یا devCode)
                                            |
                                            v
[کاربر] ---> وارد کردن کد تایید    ---> POST /api/auth/verify-code/
                                            |
                                            v
                                     ذخیره access و refresh در localStorage
                                     + انتقال خودکار سبد مهمان به کاربر
```

#### ۳.۱. درخواست ارسال کد تایید (OTP)
- **مسیر:** `POST /api/auth/send-code/`
- **Body (JSON):**
```json
{
  "phone": "09121234567"
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "devCode": "54321"
}
```
> **نکته توسعه‌دهنده:** در حالت `DEBUG=True`، کد ارسال‌شده در کلید `devCode` برگردانده می‌شود تا بدون نیاز به پنل پیامکی بتوانید به راحتی در فرانت تست کنید.

#### ۳.۲. بررسی کد تایید و ورود (Verify OTP & Login)
- **مسیر:** `POST /api/auth/verify-code/`
- **Body (JSON):**
```json
{
  "phone": "09121234567",
  "code": "54321",
  "session_key": "guest-uuid-if-any"
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "tokens": {
    "access": "eyJhbGciOiJIUzI1NiIsIn...",
    "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
  },
  "customer": {
    "id": 1,
    "name": "کاربر",
    "phone": "09121234567",
    "email": "",
    "orders": 0,
    "spent": 0,
    "joined": "1404/06/25"
  }
}
```
> **انتقال خودکار سبد مهمان:** با ارسال `session_key` در این درخواست، سبد خرید مهمان به صورت خودکار به حساب کاربری متصل و ادغام می‌شود.

#### ۳.۳. رفرش خودکار توکن (Refresh Token)
- **مسیر:** `POST /api/auth/token/refresh/`
- **Body (JSON):**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
}
```
- **Response (200 OK):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsIn..."
}
```

#### ۳.۴. خروج از حساب (Logout)
- **مسیر:** `POST /api/auth/logout/`
- **Body (JSON):**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "message": "خروج با موفقیت انجام شد"
}
```

---

### قدم ۴: سبد خرید جامع (Cart Subsystem)

سبد خرید به صورت کامل هم از **کاربران مهمان** و هم از **کاربران واردشده** پشتیبانی می‌کند:
- **برای کاربر لاگین‌شده:** هدر `Authorization: Bearer <access_token>` ارسال شود.
- **برای کاربر مهمان:** هدر `X-Session-Key: <guest-uuid>` ارسال شود (یا پارامتر `?session_key=...`).

#### ۴.۱. دریافت وضعیت سبد خرید
- **مسیر:** `GET /api/cart/`
- **Response (200 OK):**
```json
{
  "id": 12,
  "total_items": 3,
  "total_price": 18500000,
  "subtotal": 18500000,
  "discount_amount": 500000,
  "shipping_cost": 0,
  "free_shipping_threshold": 3000000,
  "final_price": 18000000,
  "coupon": {
    "code": "YALDA",
    "discount_value": 500000,
    "discount_type": "fixed",
    "discount_amount": 500000
  },
  "items": [
    {
      "id": 45,
      "product_id": 1,
      "name": "پایه وینچ سنگین",
      "sku": "WINCH-01",
      "price": 10000000,
      "quantity": 1,
      "subtotal": 10000000,
      "stock": 10,
      "image": "http://localhost:4000/media/products/images/imported/bebe24e5/01.jpg",
      "variant": null
    }
  ]
}
```

#### ۴.۲. افزودن کالا به سبد خرید
- **مسیر:** `POST /api/cart/items/`
- **Body (JSON):**
```json
{
  "product_id": 1,
  "quantity": 1,
  "variant_id": null
}
```
- **Response (201 Created):** کل آبجکت خلاصه سبد خرید آپدیت‌شده برگردانده می‌شود.

#### ۴.۳. تغییر تعداد یا حذف کالا از سبد
- **تغییر تعداد:** `PATCH /api/cart/items/:product_id/` با بدنه `{"quantity": 2, "variant_id": null}`
- **حذف کالا:** `DELETE /api/cart/items/:product_id/?variant_id=...`
- **خالی کردن کل سبد:** `DELETE /api/cart/`

#### ۴.۴. اعمال یا حذف کد تخفیف
- **اعمال کوپن:** `POST /api/cart/coupon/` با بدنه `{"code": "NOROOZ"}`
- **حذف کوپن:** `DELETE /api/cart/coupon/`

#### ۴.۵. تسویه حساب و تبدیل سبد به سفارش
- **مسیر:** `POST /api/cart/checkout/`
- **Body (JSON):**
```json
{
  "customer": "رضا محمدی",
  "phone": "09121234567",
  "address": "تهران، خیابان ولیعصر، پلاک ۱۲",
  "email": "reza@example.com",
  "shipping_method": "پست پیشتاز",
  "customer_notes": "لطفاً زنگ واحد ۳ را بزنید",
  "auto_pay": true,
  "gateway": "mock"
}
```
> **نکته کاربردی:** اگر `auto_pay: true` ارسال شود، هم‌زمان اطلاعات پرداخت در کلید `payment` برگردانده می‌شود و نیازی به فراخوانی مجدد نیست.

- **Response (201 Created):**
```json
{
  "id": 14,
  "code": "ORD-9012",
  "customer": "رضا محمدی",
  "phone": "09121234567",
  "status": "در انتظار پردازش",
  "payment": "در انتظار",
  "total": 18000000,
  "shipping_cost": 0,
  "discount_amount": 500000,
  "payment": {
    "payment_url": "/api/payment/mock-pay/AUTH-A1B2C3D4",
    "authority": "AUTH-A1B2C3D4",
    "amount": 18000000,
    "order_code": "ORD-9012"
  }
}
```

---

### قدم ۵: درگاه پرداخت الکترونیک و تست (Payment Gateway Flow)

```
[فرانت] ثبت سفارش ---> دریافت payment_url ---> انتقال کاربر به درگاه (window.location.href)
                                                       |
                                                       v
                                            پرداخت موفق در درگاه
                                                       |
                                                       v
[فرانت] صفحه بازگشت (/profile?tab=Orders) <--- Redirect از درگاه
```

1. **درخواست پرداخت مستقل:** `POST /api/payment/request/`
   - Body: `{"order_code": "ORD-9012", "gateway": "mock"}`
   - خروجی: `payment_url` جهت هدایت کاربر.
2. **درگاه تستی محیط توسعه (Mock Gateway):**
   - کاربر به آدرس `http://localhost:4000/api/payment/mock-pay/<authority>` هدایت می‌شود که یک صفحه درگاه واقعی بانکی با دکمه‌های «پرداخت موفق» و «انصراف» است.
3. **تأییدیه پرداخت (Verify):** `POST /api/payment/verify/`
   - Body: `{"authority": "AUTH-...", "status": "OK"}`
   - نتیجه: کسر موجودی قطعی، ثبت شماره پیگیری بانکی (`ref_id`)، تغییر وضعیت سفارش به «پرداخت شده» و صدور اعلان/پیامک.

---

### قدم ۶: کاتالوگ، محصولات ویژه، منتخب و شگفت‌انگیز (Products, Featured & Deals)

#### ۶.۱. اندپوینت‌های تخصصی صفحه اول و اسلایدرها:
- **محصولات ویژه و منتخب (Featured Slider):** `GET /api/products/featured/?limit=10`
- **پیشنهادات شگفت‌انگیز و تخفیف‌دار (Special Offers Deals):** `GET /api/products/special-offers/?limit=10`
- **پرفروش‌ترین محصولات (Best Sellers):** `GET /api/products/best-sellers/?limit=10`
- **جدیدترین محصولات (New Arrivals):** `GET /api/products/new-arrivals/?limit=10`
- **تغییر سریع وضعیت ویژه بودن در ادمین (Toggle Featured):** `PATCH /api/products/:id/toggle-featured/` با بدنه اختیاری `{"is_featured": true}`
- **عملیات گروهی ادمین روی محصولات (Batch Actions):** `POST /api/products/batch-action/`
  ```json
  {
    "ids": [1, 2, 5],
    "action": "set_featured" // "set_featured" | "unset_featured" | "set_active" | "set_inactive" | "delete" | "change_category"
  }
  ```

#### ۶.۲. فیلدهای هر کالا در پاسخ API:
هر آبجکت محصول شامل کلیدهای زیر است که مستقیماً با کامپوننت‌های فرانت منطبق هستند:
- `id`: شناسه عددی کالا
- `name` و `title`: نام محصول (فارسی)
- `subtitle`: زیرعنوان / نام برند
- `price`: قیمت فعلی (تومان)
- `oldPrice`: قیمت خط‌خورده قبل از تخفیف (در صورت وجود)
- `discount`: درصد تخفیف محاسبه‌شده (مثلاً ۲۰)
- `Empressive`: کالای شگفت‌انگیز / ویژه (`is_featured`)
- `rating`: امتیاز میانگین کاربران (مثلاً ۴.۸)
- `image`: **آدرس تصویر اصلی به عنوان رشته متنی** (مناسب `src={product.image}`)
- `images`: گالری تمام تصاویر محصول `[{ id, url, name }]`
- `video`: فایل ویدیو اختصاصی معرفی محصول `{ url, name }`
- `stock`: موجودی انبار
- `status`: «فعال» یا «ناموجود»
- `variants`: لیست تنوع‌ها (رنگ، سایز و...)
- `specifications`: دیکشنری مشخصات فنی کالا

#### ۶.۳. فیلترهای جستجو و مرتب‌سازی:
- **لیست همه یا فیلتر:** `GET /api/products/`
  - `?category=اسپیکر`: فیلتر دسته‌بندی
  - `?search=میکروفون`: جستجو در عنوان، برند و کد
  - `?brand=JBL`: فیلتر برند
  - `?min_price=1000000&max_price=5000000`: فیلتر بازه قیمت
  - `?in_stock=true`: فقط کالاهای موجود
  - `?is_featured=true`: کالاهای پیشنهاد شگفت‌انگیز (اسلایدر قرمز)
  - `?ordering=price_asc`: ارزان‌ترین
  - `?ordering=price_desc`: گران‌ترین
  - `?ordering=popular`: پرفروش‌ترین و پربازدیدترین
  - `?ordering=rating`: بالاترین امتیاز
  - `?ordering=newest`: جدیدترین
  - `?page=1&page_size=12`: صفحه‌بندی اختیاری

#### سایر اندپوینت‌های کاتالوگ:
- **جزئیات محصول:** `GET /api/products/:id/`
- **کالاهای مرتبط و پیشنهادی:** `GET /api/products/:id/related/`
- **مقایسه چند کالا:** `GET /api/products/compare/?ids=1,2,3`
- **لیست برندها:** `GET /api/brands/`
- **لیست دسته‌بندی‌ها:** `GET /api/categories/`
- **تنوع‌های محصول:** `GET /api/products/:id/variants/` (مشاهده و افزودن تنوع کالا)
- **ویرایش و حذف تنوع:** `PATCH /api/variants/:id/` و `DELETE /api/variants/:id/`

---

### قدم ۷: نظرات و پرسش و پاسخ کاربران (Reviews & Q&A)

#### نظرات و امتیازدهی:
- **مشاهده نظرات تاییدشده و آمار امتیاز:** `GET /api/products/:id/reviews/`
- **ثبت نظر جدید:** `POST /api/products/:id/reviews/`
```json
{
  "rating": 5,
  "comment": "کیفیت ساخت و تفکیک صدا بسیار بالاست.",
  "user_name": "امیر رضایی",
  "pros": ["بدنه مقاوم", "صدای رسا"],
  "cons": ["وزن کمی بالاست"]
}
```

#### پرسش و پاسخ:
- **مشاهده پرسش‌ها:** `GET /api/products/:id/questions/`
- **ثبت پرسش:** `POST /api/products/:id/questions/` با بدنه `{"question_text": "آیا کابل داخل کارتن هست؟"}`
- **ثبت پاسخ:** `POST /api/questions/:question_id/answers/` با بدنه `{"answer_text": "بله، کابل اورجینال موجود است."}`

---

### قدم ۸: پروفایل کاربری و پنل مشتری (Profile, Orders, Addresses)

#### ۸.۱. مشخصات فردی
- **دریافت اطلاعات:** `GET /api/me/`
- **ویرایش مشخصات:** `PUT /api/me/`
```json
{
  "NameAndFamily": "سارا محمدی",
  "BirthDate": "1375/04/12",
  "IdCard": "0012345678",
  "Email": "sara@example.com",
  "Number": "09121234567",
  "gender": "زن"
}
```
- **آپلود آواتار:** `POST /api/me/avatar/` با فرم‌دیتای کلید `avatar`.

#### ۸.۲. لیست سفارش‌های کاربر در تب‌های پروفایل
- **مسیر:** `GET /api/me/orders/`
- **پاسخ ساختاریافته ویژه کامپوننت `Profile.jsx`:**
```json
{
  "InProgress": [ { "id": 1, "code": "ORD-9010", "status": "در حال ارسال", "total": 12500000, ... } ],
  "Delivered": [ ... ],
  "Returned": [ ... ],
  "Canceled": [ ... ]
}
```

#### ۸.۳. لغو سفارش توسط مشتری
- **مسیر:** `POST /api/orders/:code/cancel/`
- **Body:** `{"reason": "انصراف از خرید"}`
- موجودی کالاهای سفارش داده‌شده به طور خودکار به انبار بازگردانده می‌شود.

#### ۸.۴. فاکتور چاپی سفارش
- **آدرس وب فاکتور:** `http://localhost:4000/api/orders/:code/invoice/`
- آماده چاپ مستقیم یا باز شدن در تگ `<iframe>` / پنجره جدید.

#### ۸.۵. مدیریت آدرس‌ها
- **لیست آدرس‌ها:** `GET /api/addresses/`
- **ثبت آدرس جدید:** `POST /api/addresses/`
```json
{
  "title": "محل کار",
  "recipient_name": "سارا محمدی",
  "recipient_phone": "09121234567",
  "province": "تهران",
  "city": "تهران",
  "address": "خیابان آزادی، خیابان حبیب‌الهی، پلاک ۲۰",
  "postal_code": "1458899999",
  "is_default": true
}
```
- **حذف آدرس:** `DELETE /api/addresses/:id/`
- **تعیین پیش‌فرض:** `PATCH /api/addresses/:id/`

#### ۸.۶. علاقه‌مندی‌ها (Wishlist)
- **مشاهده لیست:** `GET /api/favorites/`
- **افزودن کالا:** `POST /api/favorites/:product_id/`
- **حذف کالا:** `DELETE /api/favorites/:product_id/`

#### ۸.۷. پیام‌ها و اعلان‌ها (Notifications)
- **لیست پیام‌ها:** `GET /api/me/messages/`
- **خواندن یک پیام:** `PATCH /api/me/messages/:id/read/`
- **خواندن تمام پیام‌ها:** `POST /api/me/messages/read-all/`

---

### قدم ۹: اسلاید شو ها، بنرها و صفحه اصلی (Slideshows & Marketing)

#### ۹.۱. مدیریت بنرها و اسلایدرها (Banners CRUD):
- **لیست بنرهای فعال صفحه اصلی:** `GET /api/banners/?type=hero` (یا `type=promo` برای بنرهای میانی)
- **لیست همه بنرها برای پنل ادمین:** `GET /api/banners/?all=true`
- **ایجاد بنر جدید (توسط ادمین):** `POST /api/banners/` (ارسال به صورت `multipart/form-data`)
  - فیلدها: `title`, `subtitle`, `image` (فایل عکس), `link_url`, `banner_type` (`hero` | `promo` | `sidebar`), `display_order`, `is_active`
- **جزئیات بنر:** `GET /api/banners/:id/`
- **ویرایش بنر:** `PATCH /api/banners/:id/` (امکان تغییر تصویر، لینک و وضعیت فعال بودن)
- **حذف بنر:** `DELETE /api/banners/:id/` (حذف رکورد و فایل فیزیکی عکس)
- **تغییر ترتیب نمایش اسلایدها (Reorder):** `POST /api/banners/reorder/`
  ```json
  {
    "order": [
      { "id": 3, "display_order": 0 },
      { "id": 1, "display_order": 1 },
      { "id": 2, "display_order": 2 }
    ]
  }
  ```

#### ۹.۲. وبلاگ، تماس با ما و تنظیمات فروشگاه:
- **لیست مقالات و وبلاگ:** `GET /api/articles/`
- **جزئیات مقاله و ویدیوها:** `GET /api/articles/:id/`
- **فرم تماس با ما:** `POST /api/contact/` با بدنه `{"name": "...", "phone": "...", "subject": "...", "message": "..."}`
- **خبرنامه:** `POST /api/newsletter/subscribe/` با بدنه `{"email_or_phone": "0912..."}`
- **مشاهده تنظیمات فروشگاه:** `GET /api/site-settings/`
- **ویرایش تنظیمات فروشگاه توسط ادمین:** `PATCH /api/site-settings/`
  ```json
  {
    "title": "فروشگاه تجهیزات صوتی آوای انعکاس",
    "phone_support": "021-66700000",
    "email_support": "info@avayenekas.com",
    "address": "تهران، خیابان جمهوری...",
    "free_shipping_threshold": 3000000,
    "default_shipping_cost": 45000
  }
  ```

---

### قدم ۱۰: پنل ادمین اختصاصی و گزارشات (Admin Panel & Reports)

#### ۱۰.۱. شاخص‌ها و متریک‌های تحلیلی داشبورد (Dashboard Metrics):
- **مسیر:** `GET /api/admin/dashboard/metrics/`
- **خروجی جامع شامل:**
  - `summary`: مجموع فروش، درآمد کل، تعداد کل سفارشات، تعداد کل محصولات، کالاهای رو به اتمام، تعداد کل مشتریان، ارزش ریالی کل انبار (`total_inventory_value`)، تعداد اقلام انبار (`total_inventory_items`)
  - `sales_by_month`: آرایه فروش در ۱۲ ماه سال شمسی جهت ترسیم نمودار میله‌ای/خطی در پنل ادمین:
    ```json
    [
      { "month": "فروردین", "sales": 32000000 },
      { "month": "اردیبهشت", "sales": 41000000 },
      ...
    ]
    ```
  - `category_share`: سهم هر دسته‌بندی از موجودی و فروش جهت ترسیم نمودار دایره‌ای (PieChart):
    ```json
    [
      { "name": "اسپیکر", "value": 32 },
      { "name": "هدفون", "value": 26 },
      ...
    ]
    ```
  - `orders_by_status`: تفکیک سفارش‌ها بر اساس ۵ وضعیت مجاز
  - `low_stock_alerts`: لیست ۱۰ کالای کم‌موجودی جهت هشدار تأمین انبار
  - `recent_orders`: آخرین سفارشات ثبت‌شده

#### ۱۰.۲. مدیریت مشتریان در پنل ادمین:
- **لیست مشتریان با جستجو:** `GET /api/customers/?search=0912...`
- **مشاهده پرونده کامل مشتری، آدرس‌ها و تمام سفارشات:** `GET /api/customers/:id/`
- **ویرایش وضعیت مشتری (فعال/مسدودسازی):** `PATCH /api/customers/:id/` با بدنه `{"is_active": false}`

#### ۱۰.۳. مدیریت سفارشات:
- **لیست سفارش‌ها:** `GET /api/orders/`
- **تغییر وضعیت سفارش توسط ادمین:** `PATCH /api/orders/:code/status/` با بدنه `{"status": "در حال ارسال", "comment": "تحویل تیپاکس شد"}`
- **ثبت کد رهگیری پستی و یادداشت:** `PATCH /api/orders/:code/` با بدنه `{"tracking_code": "18492048590", "shipping_method": "تیپاکس"}`
- **حذف سفارش:** `DELETE /api/orders/:code/`

#### ۱۰.۴. مدیریت کوپن‌های تخفیف (Admin Coupons CRUD):
- **لیست کوپن‌ها:** `GET /api/admin/coupons/`
- **ایجاد کوپن جدید:** `POST /api/admin/coupons/`
  ```json
  {
    "code": "YALDA40",
    "discount_type": "percent", // یا "fixed"
    "discount_value": 40,
    "max_discount_amount": 1000000,
    "min_purchase_amount": 2000000,
    "usage_limit": 100,
    "is_active": true
  }
  ```
- **ویرایش کوپن:** `PATCH /api/admin/coupons/:id/`
- **حذف کوپن:** `DELETE /api/admin/coupons/:id/`

#### ۱۰.۵. مدیریت نظرات و تایید آن‌ها:
- **لیست نظرات:** `GET /api/admin/reviews/?approved=false`
- **تایید یا رد نظر:** `PATCH /api/admin/reviews/:id/` با بدنه `{"is_approved": true}`
- **حذف نظر:** `DELETE /api/admin/reviews/:id/`

#### ۱۰.۶. مدیریت پیام‌های تماس با ما:
- **لیست پیام‌ها:** `GET /api/admin/contact-messages/?responded=false`
- **علامت‌گذاری پاسخ‌داده‌شده:** `PATCH /api/admin/contact-messages/:id/` با بدنه `{"is_responded": true}`
- **حذف پیام:** `DELETE /api/admin/contact-messages/:id/`

---

## ۳. جدول کدهای وضعیت HTTP (Status Codes)

| کد HTTP | مفهوم | کاربرد در API |
| :--- | :--- | :--- |
| `200 OK` | موفق | درخواست با موفقیت انجام شد و داده‌ها در بدنه ارسال گردید. |
| `201 Created` | ساخته شد | محصول، سفارش، آدرس یا آیتم جدید با موفقیت ایجاد شد. |
| `400 Bad Request` | خطای اعتبارسنجی | پارامترهای ارسالی ناقص یا اشتباه است (پیام خطا در کلید `error` قرار دارد). |
| `401 Unauthorized` | عدم احراز هویت | توکن JWT ارسال نشده، نامعتبر است یا منقضی شده است. |
| `403 Forbidden` | عدم دسترسی | کاربر مجوز لازم برای انجام عملیات مورد نظر را ندارد. |
| `404 Not Found` | یافت نشد | محصول، سفارش، دسته‌بندی یا آدرس درخواستی وجود ندارد. |
| `429 Too Many Requests` | محدودیت درخواست | به دلیل درخواست‌های بیش از حد (Throttling) دسترسی موقتاً محدود شده است. |
| `500 Server Error` | خطای داخلی سرور | خطای برنامه‌نویسی یا پایگاه‌داده رخ داده است. |

---

## ۴. نمونه کد آماده React برای اتصال کامپوننت‌ها

### نمونه ۱: اتصال اسلایدر محصولات شگفت‌انگیز (`SwiperEmpresive.jsx`)
```jsx
import React, { useState, useEffect } from "react";
import { ProductApi } from "../api/shopApi";

export default function EmperiseveSwiper() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ProductApi.getProducts({ is_featured: true })
      .then((data) => {
        // در صورت فعال بودن صفحه‌بندی، data.results وگرنه data
        const list = Array.isArray(data) ? data : data.results || [];
        setProducts(list);
      })
      .catch((err) => console.error("خطا در بارگذاری پیشنهادات شگفت‌انگیز:", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>در حال بارگذاری...</div>;

  return (
    <div className="swiper-container">
      {products.map((product) => (
        <div key={product.id} className="product-card">
          <img src={product.image} alt={product.title} />
          <h3>{product.title}</h3>
          <span>{product.price.toLocaleString("fa-IR")} تومان</span>
        </div>
      ))}
    </div>
  );
}
```

### نمونه ۲: اتصال افزودن به سبد خرید
```jsx
import { CartApi } from "../api/shopApi";

async function handleAddToCart(productId) {
  try {
    const updatedCart = await CartApi.addItem(productId, 1);
    alert("کالا به سبد خرید اضافه شد!");
    console.log("خلاصه سبد:", updatedCart);
  } catch (error) {
    alert(error.message);
  }
}
```

---

## ۵. چک‌لیست تحویل نهایی و پایش سیستم

- [x] مدل‌های پایگاه داده استاندارد و مهاجرت‌ها (Migrations) کامل اجرا شده است.
- [x] سیستم احراز هویت پیامکی بدون پسورد (OTP) + JWT Tokens پیاده‌سازی شده است.
- [x] سبد خرید دوگانه (مهمان با `X-Session-Key` و کاربر واردشده با ادغام خودکار) فعال است.
- [x] سیستم کوپن‌های درصدی و ریالی با سقف خرید و اعتبارسنجی خودکار تست شده است.
- [x] ثبت سفارش اتمیک با قفل هم‌زمانی (`select_for_update`) و کاهش/بازگردانی موجودی انبار فعال است.
- [x] درگاه پرداخت تستی داخلی (`mock_payment_page`) و تأییدیه زرین‌پال پیاده‌سازی شده است.
- [x] پنل ادمین با پشتیبانی کامل از آپلود چندگانه تصاویر و ویدیوها آماده است.
- [x] ماژول فرانت‌اند آماده `Front/AvayEnekas/src/api/shopApi.js` ایجاد گردید.
