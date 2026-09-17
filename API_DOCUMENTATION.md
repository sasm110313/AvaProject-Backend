# راهنمای جامع اتصال و استفاده از API بک‌اند (ویژه توسعه‌دهنده فرانت‌اند)

این مستند راهنمای کامل و گام‌به‌گام اتصال پروژه‌ی فرانت‌اند (React / Vite) به بک‌اند جنگو است. تمام مسیرها (Endpoints)، فرمت درخواست‌ها، نمونه پاسخ‌ها و نکات کلیدی در این سند گردآوری شده‌اند.

---

## ۱. مشخصات عمومی سرور و اتصال

- **آدرس پایه API (Base URL):** `http://localhost:4000/api`
- **آدرس فایل‌های چندرسانه‌ای (عکس/ویدیو):** `http://localhost:4000/media/...`
- **تنظیمات CORS:** برای پورت پیش‌فرض فرانت (`http://localhost:5173` و `http://127.0.0.1:5173`) با هدرهای استاندارد و پشتیبانی از Credentials فعال است.
- **فعال‌سازی در فرانت:** در فایل `Front/AvayEnekas/src/Components/AdminPannel/Api.jsx` کافیست مقدار `USE_MOCK_DATA = false` قرار داده شود.

---

## ۲. احراز هویت و مدیریت نشست (Authentication & JWT)

احراز هویت بر اساس شماره موبایل و کد یک‌بار مصرف (OTP) است. خروجی ورود شامل جفت توکن استاندارد JWT است.

### هدر احراز هویت (در صورت لاگین بودن کاربر):
```http
Authorization: Bearer <access_token>
```

---

### ۲.۱. درخواست ارسال کد تایید (OTP)
- **مسیر:** `POST /auth/send-code`
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
> **نکته برای فرانت‌کار:** در محیط توسعه (`DEBUG=True`)، کد ارسال‌شده در کلید `devCode` برگردانده می‌شود تا تست در فرانت بدون نیاز به پنل پیامکی به سادگی انجام شود.

---

### ۲.۲. بررسی کد تایید و ورود (Verify OTP & Login)
- **مسیر:** `POST /auth/verify-code`
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
> **نکته سبد خرید:** اگر کاربر پیش از ورود، کالاهایی را به عنوان مهمان به سبد خرید اضافه کرده باشد، با ارسال `session_key` در این درخواست، سبد خرید مهمان به صورت خودکار به حساب کاربری او منتقل می‌شود.

---

### ۲.۳. تازه‌سازی توکن (Refresh Token)
- **مسیر:** `POST /auth/token/refresh`
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

---

## ۳. سبد خرید (Cart Subsystem)

سبد خرید به صورت کامل هم از **کاربران مهمان** و هم از **کاربران لاگین‌شده** پشتیبانی می‌کند.

- **برای کاربر لاگین‌شده:** هدر `Authorization: Bearer <token>` ارسال شود.
- **برای کاربر مهمان:** هدر `X-Session-Key: <یک رشته دلخواه یا uuid>` یا پارامتر `?session_key=...` ارسال شود.

### ۳.۱. دریافت اطلاعات سبد خرید
- **مسیر:** `GET /cart`
- **Response (200 OK):**
```json
{
  "id": 1,
  "total_items": 3,
  "total_price": 25000000,
  "items": [
    {
      "id": 10,
      "product_id": 1,
      "name": "اسپیکر مانیتورینگ JBL",
      "sku": "SPK-1001",
      "price": 12500000,
      "quantity": 2,
      "subtotal": 25000000,
      "stock": 14,
      "image": "http://localhost:4000/media/products/images/sample.jpg"
    }
  ]
}
```

### ۳.۲. افزودن کالا به سبد خرید
- **مسیر:** `POST /cart/items`
- **Body (JSON):**
```json
{
  "product_id": 1,
  "quantity": 1
}
```
- **Response (201 Created):** آبجکت خلاصه سبد خرید به‌روزرسانی‌شده.

### ۳.۳. تغییر تعداد یا حذف کالا در سبد
- **تغییر تعداد:** `PATCH /cart/items/<product_id>` با بدنه `{"quantity": 3}` (اگر 0 ارسال شود، کالا حذف می‌شود).
- **حذف کالا:** `DELETE /cart/items/<product_id>`
- **خالی کردن کل سبد:** `DELETE /cart`

### ۳.۴. تسویه حساب مستقیم سبد خرید (Checkout Cart)
- **مسیر:** `POST /cart/checkout`
- **Body (JSON):**
```json
{
  "customer": "علی محمدی",
  "phone": "09121234567",
  "address": "تهران، خیابان ولیعصر، پلاک ۱",
  "email": "ali@example.com"
}
```
- **Response (201 Created):** آبجکت سفارش ایجاد‌شده با شماره سفارش (`code`). در این مرحله سبد خرید به صورت خودکار خالی شده و از موجودی انبار کسر می‌گردد.

---

## ۴. محصولات و کاتالوگ (Products)

این بخش با پنل ادمین فرانت (`AdminPannel/Api.jsx`) و همچنین کاتالوگ صفحه اصلی و سوایپرها (`ProductData.js`) سازگاری دوطرفه دارد.

### ۴.۱. لیست محصولات
- **مسیر:** `GET /products`
- **پارامترهای اختیاری فیلتر:**
  - `?category=اسپیکر`
  - `?search=JBL`
- **نمونه آیتم در آرایه خروجی:**
```json
{
  "id": 1,
  "name": "اسپیکر مانیتورینگ استودیویی JBL 305P",
  "title": "اسپیکر مانیتورینگ استودیویی JBL 305P",
  "subtitle": "JBL",
  "category": "اسپیکر",
  "sku": "SPK-1001",
  "price": 12500000,
  "oldPrice": 14000000,
  "discount": 11,
  "rating": 4.8,
  "Empressive": true,
  "stock": 14,
  "status": "فعال",
  "threshold": 5,
  "images": [
    {
      "id": 1,
      "url": "http://localhost:4000/media/products/images/...",
      "name": "jbl-front.jpg"
    }
  ],
  "video": {
    "url": "http://localhost:4000/media/products/videos/...",
    "name": "preview.mp4"
  }
}
```

### ۴.۲. جزئیات، ایجاد، ویرایش و حذف محصول
- **جزئیات محصول:** `GET /products/:id`
- **ایجاد محصول:** `POST /products` (با فرمت `multipart/form-data` شامل فایل‌های `images` و `video`)
- **ویرایش محصول:** `PUT /products/:id` (با فرمت `multipart/form-data` شامل `existingImageUrls` برای حفظ عکس‌های قبلی)
- **حذف محصول:** `DELETE /products/:id` (پاسخ: `{"success": true}`)
- **لیست دسته‌بندی‌ها:** `GET /categories` (خروجی: آرایه‌ای از نام دسته‌ها)

---

## ۵. سفارش‌ها (Orders)

### ۵.۱. لیست سفارشات و ثبت مستقیم سفارش
- **دریافت سفارشات:** `GET /orders`
- **ثبت سفارش مستقیم (بدون سبد خرید):** `POST /orders`
  - **Body (JSON):**
  ```json
  {
    "customer": "علی محمدی",
    "phone": "09121234567",
    "address": "تهران، خیابان آزادی",
    "email": "ali@example.com",
    "status": "در انتظار پردازش",
    "payment": "در انتظار",
    "items": [
      { "product_id": 1, "quantity": 2 }
    ]
  }
  ```

### ۵.۲. جزئیات، تغییر وضعیت و حذف سفارش
- **جزئیات سفارش:** `GET /orders/:code` (هم کد مثل `ORD-9001` و هم آیدی عددی پشتیبانی می‌شود).
- **تغییر وضعیت سفارش (در پنل ادمین):**
  - **مسیر:** `PATCH /orders/:code/status`
  - **Body (JSON):** `{"status": "در حال ارسال"}`
  - وضعیت‌های مجاز: `"در انتظار پردازش"`, `"در حال ارسال"`, `"تحویل شده"`, `"لغو شده"`
  > **نکته انبار:** در صورتی که سفارش به وضعیت `"لغو شده"` تغییر یابد، موجودی کالاهای آن به صورت خودکار به انبار بازگردانده می‌شود.
- **حذف سفارش:** `DELETE /orders/:code`

---

## ۶. مشتریان و کاربران (Customers & Users)

جدول مشتریان و کاربران سیستم کاملاً یکپارچه هستند.

- **لیست مشتریان (برای پنل ادمین):** `GET /customers`
  - خروجی:
  ```json
  [
    {
      "id": 1,
      "name": "علی محمدی",
      "phone": "09121111111",
      "email": "ali.m@example.com",
      "orders": 6,
      "spent": 89400000,
      "joined": "1404/06/25"
    }
  ]
  ```

---

## ۷. پنل کاربری و پروفایل (Profile, Orders, Addresses, Favorites)

تمامی اندپوینت‌های مورد نیاز برای کامپوننت `Profile.jsx` آماده و متصل است:

### ۷.۱. اطلاعات پروفایل
- **دریافت اطلاعات:** `GET /me` (از طریق توکن لاگین یا پارامتر `?phone=0912...`)
- **ویرایش اطلاعات:** `PUT /me`
  - **Body (JSON):**
  ```json
  {
    "NameAndFamily": "سید محمد محمدی",
    "BirthDate": "1375/04/10",
    "IdCard": "0012345678",
    "Email": "mohammadi@example.com",
    "Number": "09027741653",
    "gender": "male"
  }
  ```

### ۷.۲. سفارشات کاربر در تب‌های پروفایل
- **مسیر:** `GET /me/orders`
- **پاسخ:** این پاسخ دقیقا به صورت تفکیک‌شده بر اساس تب‌های کامپوننت `Profile.jsx` ارسال می‌شود:
```json
{
  "InProgress": [ /* لیست سفارشات جاری */ ],
  "Delivered": [ /* لیست سفارشات تحویل‌شده */ ],
  "Returned": [ /* لیست مرجوع‌شده‌ها */ ],
  "Canceled": [ /* لیست سفارشات لغو‌شده */ ]
}
```

### ۷.۳. مدیریت آدرس‌ها
- **دریافت لیست آدرس‌ها:** `GET /addresses`
- **ثبت آدرس جدید:** `POST /addresses` با بدنه `{"title": "منزل", "address": "تهران میدان ونک", "postal_code": "12345"}`
- **تعیین آدرس پیش‌فرض:** `PATCH /addresses/:id`
- **حذف آدرس:** `DELETE /addresses/:id`

### ۷.۴. لیست علاقه‌مندی‌ها (Wishlist)
- **مشاهده لیست:** `GET /favorites` (خروجی: آرایه‌ای از محصولات موردعلاقه)
- **افزودن به علاقه‌مندی‌ها:** `POST /favorites/:product_id`
- **حذف از علاقه‌مندی‌ها:** `DELETE /favorites/:product_id`

---

## ۸. مقالات و وبلاگ (Articles)

- **لیست مقالات:** `GET /articles`
- **جزئیات مقاله:** `GET /articles/:id`
- **ایجاد مقاله:** `POST /articles` (`multipart/form-data` شامل فیلدهای `coverImage` و فایل‌های `videos`)
- **ویرایش مقاله:** `PUT /articles/:id` (`multipart/form-data` با ارسال `existingVideoUrls` و `existingCoverImageUrl`)
- **حذف مقاله:** `DELETE /articles/:id`

---

## ۹. داشبورد تحلیلی ادمین (Admin Analytics)

این اندپوینت برای نمایش شاخص‌های عملکردی و رسم نمودار در پنل ادمین (`AdminPannel.jsx`) طراحی شده است:

- **مسیر:** `GET /admin/dashboard/metrics`
- **نمونه خروجی:**
```json
{
  "summary": {
    "total_revenue": 214500000,
    "total_orders": 10,
    "total_products": 15,
    "low_stock_count": 3,
    "total_customers": 8
  },
  "orders_by_status": {
    "در انتظار پردازش": 3,
    "در حال ارسال": 3,
    "تحویل شده": 3,
    "لغو شده": 1
  },
  "low_stock_alerts": [
    {
      "id": 7,
      "name": "اسپیکر پرتابل JBL Charge 5",
      "stock": 0,
      "threshold": 6
    }
  ],
  "recent_orders": [
    {
      "id": "ORD-9010",
      "customer": "الناز جعفری",
      "date": "1404/05/25",
      "items": 3,
      "total": 22300000,
      "status": "در انتظار پردازش",
      "payment": "در انتظار"
    }
  ],
  "top_selling_products": [
    {
      "product_id": 1,
      "product_name": "اسپیکر مانیتورینگ استودیویی JBL 305P",
      "total_sold": 4
    }
  ],
  "sales_trend": [
    { "date": "1404/05/20", "sales": 21400000 },
    { "date": "1404/05/21", "sales": 8900000 }
  ]
}
```

---

## ۱۰. جدول کدهای وضعیت HTTP (Status Codes)

| کد وضعیت | معنی | مورد کاربرد |
|---|---|---|
| `200 OK` | موفق | درخواست‌های GET, PUT, PATCH |
| `201 Created` | ایجاد شد | ثبت موفق محصول، سفارش، آیتم سبد، آدرس، توکن |
| `400 Bad Request` | دیتای نامعتبر | خطای اعتبارسنجی فیلدها، کمبود موجودی انبار، کد OTP اشتباه |
| `401 Unauthorized` | عدم احراز هویت | عدم ارسال یا نامعتبر بودن توکن JWT |
| `404 Not Found` | یافت نشد | محصول، سفارش یا مقاله پیدا نشد |
| `500 Server Error` | خطای سرور | خطاهای غیرمنتظره بک‌اند |
