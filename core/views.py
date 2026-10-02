from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.models import (
    Address,
    Article,
    Banner,
    Category,
    ContactMessage,
    Coupon,
    Favorite,
    NewsletterSubscriber,
    Notification,
    Order,
    OrderStatusHistory,
    PaymentTransaction,
    Product,
    ProductAnswer,
    ProductQuestion,
    ProductReview,
    ProductVariant,
    SiteSetting,
    User,
)
from core.pagination import ConditionalPageNumberPagination
from core.serializers import (
    AddressSerializer,
    ArticleSerializer,
    BannerSerializer,
    CartSerializer,
    CategorySerializer,
    ContactMessageSerializer,
    CouponSerializer,
    CustomerSerializer,
    FavoriteSerializer,
    NewsletterSubscriberSerializer,
    NotificationSerializer,
    OrderItemSerializer,
    OrderSerializer,
    OrderStatusHistorySerializer,
    PaymentTransactionSerializer,
    ProductAnswerSerializer,
    ProductQuestionSerializer,
    ProductReviewSerializer,
    ProductSerializer,
    ProductVariantSerializer,
    ProfileSerializer,
    SiteSettingSerializer,
)
from core.services.analytics_service import AnalyticsService
from core.services.auth_service import AuthService
from core.services.cart_service import CartService
from core.services.category_service import CategoryService
from core.services.coupon_service import CouponService
from core.services.notification_service import NotificationService
from core.services.order_service import OrderService
from core.services.payment_service import PaymentService
from core.services.product_service import ProductService
from core.services.review_service import ReviewService
from core.throttling import (
    AnonRateThrottle,
    BurstRateThrottle,
    OrderCreateRateThrottle,
    OtpRateThrottle,
    OtpVerifyRateThrottle,
    UserRateThrottle,
)

DEFAULT_CATEGORIES = [
    "اسپیکر",
    "هدفون",
    "آمپلی‌فایر",
    "میکروفون",
    "میکسر",
    "کابل و اتصالات",
]


# ============================================================================
# PRODUCTS & CATALOG
# ============================================================================

@extend_schema(
    summary="لیست یا جستجوی محصولات با فیلتر پیشرفته",
    parameters=[
        OpenApiParameter("category", str, description="نام یا اسلاگ دسته‌بندی"),
        OpenApiParameter("search", str, description="جستجو در نام، توضیحات، برند یا کد کالا"),
        OpenApiParameter("brand", str, description="نام برند"),
        OpenApiParameter("min_price", int, description="حداقل قیمت به تومان"),
        OpenApiParameter("max_price", int, description="حداکثر قیمت به تومان"),
        OpenApiParameter("in_stock", bool, description="فقط کالاهای موجود"),
        OpenApiParameter("is_featured", bool, description="فقط کالاهای منتخب/ویژه"),
        OpenApiParameter("ordering", str, description="مرتب‌سازی: price_asc, price_desc, newest, popular, rating"),
        OpenApiParameter("page", int, description="شماره صفحه"),
        OpenApiParameter("page_size", int, description="تعداد در هر صفحه"),
    ],
)
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def product_list(request: Any) -> Response:
    if request.method == "GET":
        category = request.query_params.get("category")
        search = request.query_params.get("search")
        brand = request.query_params.get("brand")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        in_stock_raw = request.query_params.get("in_stock")
        is_featured_raw = request.query_params.get("is_featured")
        ordering = request.query_params.get("ordering")

        in_stock = True if in_stock_raw in ("true", "1") else (False if in_stock_raw in ("false", "0") else None)
        is_featured = True if is_featured_raw in ("true", "1") else (False if is_featured_raw in ("false", "0") else None)

        products = ProductService.list_products(
            category=category,
            search=search,
            brand=brand,
            min_price=int(min_price) if min_price and min_price.isdigit() else None,
            max_price=int(max_price) if max_price and max_price.isdigit() else None,
            in_stock=in_stock,
            is_featured=is_featured,
            ordering=ordering,
        )

        paginator = ConditionalPageNumberPagination()
        page = paginator.paginate_queryset(products, request)
        if page is not None:
            serializer = ProductSerializer(page, many=True, context={"request": request})
            return paginator.get_paginated_response(serializer.data)

        serializer = ProductSerializer(products, many=True, context={"request": request})
        return Response(serializer.data)

    serializer = ProductSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="جزئیات، ویرایش یا حذف یک محصول")
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def product_detail(request: Any, pk: int) -> Response:
    try:
        product = ProductService.get_product(product_id=pk, track_view=(request.method == "GET"))
    except Product.DoesNotExist:
        return Response({"error": "محصول یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ProductSerializer(product, context={"request": request})
        return Response(serializer.data)

    if request.method == "DELETE":
        product.delete()
        return Response({"success": True})

    serializer = ProductSerializer(
        product,
        data=request.data,
        partial=(request.method == "PATCH"),
        context={"request": request},
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="لیست برندهای موجود در فروشگاه")
@api_view(["GET"])
@permission_classes([AllowAny])
def brand_list(request: Any) -> Response:
    brands = (
        Product.objects.filter(is_active=True)
        .exclude(brand="")
        .values("brand")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return Response(brands)


@extend_schema(summary="کالاهای مشابه و پیشنهادی")
@api_view(["GET"])
@permission_classes([AllowAny])
def related_products(request: Any, pk: int) -> Response:
    product = Product.objects.filter(pk=pk).first()
    if not product:
        return Response({"error": "محصول یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    related = (
        Product.objects.filter(is_active=True)
        .filter(Q(category=product.category) | Q(brand=product.brand))
        .exclude(id=product.id)
        .distinct()[:8]
    )
    return Response(ProductSerializer(related, many=True, context={"request": request}).data)


@extend_schema(summary="مقایسه فنی چند کالا در کنار هم")
@api_view(["GET"])
@permission_classes([AllowAny])
def compare_products(request: Any) -> Response:
    raw_ids = request.query_params.get("ids", "")
    try:
        id_list = [int(i.strip()) for i in raw_ids.split(",") if i.strip().isdigit()]
    except ValueError:
        id_list = []

    if not id_list:
        return Response({"error": "شناسه محصولات برای مقایسه معتبر نیست (مثال: ?ids=1,2,3)"}, status=status.HTTP_400_BAD_REQUEST)

    products = list(Product.objects.filter(id__in=id_list[:4]).prefetch_related("product_images"))
    if not products:
        return Response({"error": "هیچ‌کدام از محصولات موردنظر یافت نشدند"}, status=status.HTTP_404_NOT_FOUND)

    # Gather all specification keys across products
    all_spec_keys = []
    for p in products:
        if isinstance(p.specifications, dict):
            for k in p.specifications.keys():
                if k not in all_spec_keys:
                    all_spec_keys.append(k)

    return Response({
        "products": ProductSerializer(products, many=True, context={"request": request}).data,
        "spec_keys": all_spec_keys,
    })


# ============================================================================
# PRODUCT REVIEWS & QUESTIONS
# ============================================================================

@extend_schema(summary="مشاهده یا ثبت نظر و امتیاز برای محصول")
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def product_reviews(request: Any, pk: int) -> Response:
    if request.method == "GET":
        summary = ReviewService.get_product_reviews(product_id=pk)
        serialized_reviews = ProductReviewSerializer(summary["reviews"], many=True).data
        return Response({
            "average_rating": summary["average_rating"],
            "total_reviews": summary["total_reviews"],
            "distribution": summary["distribution"],
            "reviews": serialized_reviews,
        })

    data = request.data
    rating = int(data.get("rating", 5))
    comment = str(data.get("comment", "")).strip()
    user_name = str(data.get("user_name", "")).strip()
    pros = data.get("pros", [])
    cons = data.get("cons", [])

    try:
        review = ReviewService.add_review(
            product_id=pk,
            rating=rating,
            comment=comment,
            user=request.user if request.user.is_authenticated else None,
            user_name=user_name,
            pros=pros if isinstance(pros, list) else [],
            cons=cons if isinstance(cons, list) else [],
        )
        return Response(ProductReviewSerializer(review).data, status=status.HTTP_201_CREATED)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="مشاهده یا ثبت پرسش درباره محصول")
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def product_questions(request: Any, pk: int) -> Response:
    product = Product.objects.filter(pk=pk).first()
    if not product:
        return Response({"error": "محصول یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        questions = ProductQuestion.objects.filter(product=product, is_approved=True).prefetch_related("answers")
        return Response(ProductQuestionSerializer(questions, many=True).data)

    question_text = str(request.data.get("question_text", "")).strip()
    if not question_text:
        return Response({"error": "متن پرسش نمی‌تواند خالی باشد"}, status=status.HTTP_400_BAD_REQUEST)

    user_name = str(request.data.get("user_name", "")).strip()
    if request.user.is_authenticated:
        user_name = request.user.name or request.user.phone
    elif not user_name:
        user_name = "کاربر مهمان"

    q = ProductQuestion.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        user_name=user_name,
        question_text=question_text,
        is_approved=True,
    )
    return Response(ProductQuestionSerializer(q).data, status=status.HTTP_201_CREATED)


@extend_schema(summary="ثبت پاسخ به یک پرسش محصول")
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def question_answers(request: Any, question_id: int) -> Response:
    question = ProductQuestion.objects.filter(pk=question_id).first()
    if not question:
        return Response({"error": "پرسش یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    answer_text = str(request.data.get("answer_text", "")).strip()
    if not answer_text:
        return Response({"error": "متن پاسخ الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

    is_admin = bool(request.user.is_authenticated and request.user.is_staff)
    user_name = str(request.data.get("user_name", "")).strip()
    if request.user.is_authenticated:
        user_name = "کارشناس آوای انعکاس" if is_admin else (request.user.name or request.user.phone)
    elif not user_name:
        user_name = "کاربر"

    ans = ProductAnswer.objects.create(
        question=question,
        user=request.user if request.user.is_authenticated else None,
        user_name=user_name,
        answer_text=answer_text,
        is_admin_answer=is_admin,
        is_approved=True,
    )
    return Response(ProductAnswerSerializer(ans).data, status=status.HTTP_201_CREATED)


# ============================================================================
# CATEGORIES
# ============================================================================

@extend_schema(summary="لیست دسته‌بندی‌ها")
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def category_list(request: Any) -> Response:
    if request.method == "POST":
        try:
            cat = CategoryService.create_category(request.data)
            return Response(CategorySerializer(cat, context={"request": request}).data, status=status.HTTP_201_CREATED)
        except ValidationError as exc:
            return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)

    full = request.query_params.get("full", "").lower() in ("true", "1")
    if full:
        categories = CategoryService.list_categories(parent_only=False)
        return Response(CategorySerializer(categories, many=True, context={"request": request}).data)

    db_categories = list(Product.objects.values_list("category", flat=True).distinct())
    cat_model_names = list(Category.objects.filter(is_active=True).values_list("name", flat=True))
    all_categories = sorted(list(set(DEFAULT_CATEGORIES + [c for c in db_categories if c] + cat_model_names)))
    return Response(all_categories)


@extend_schema(summary="جزئیات دسته‌بندی با اسلاگ یا شناسه")
@api_view(["GET", "PUT", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def category_detail(request: Any, identifier: str) -> Response:
    try:
        cat = CategoryService.get_category(identifier)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(CategorySerializer(cat, context={"request": request}).data)

    if request.method == "DELETE":
        cat.delete()
        return Response({"success": True})

    serializer = CategorySerializer(cat, data=request.data, partial=True, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ORDERS & CHECKOUT & INVOICE
# ============================================================================

@extend_schema(summary="لیست یا ایجاد سفارش جدید")
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@throttle_classes([OrderCreateRateThrottle])
@csrf_exempt
def order_list(request: Any) -> Response:
    if request.method == "GET":
        orders = Order.objects.all().prefetch_related("order_items", "status_history")
        paginator = ConditionalPageNumberPagination()
        page = paginator.paginate_queryset(orders, request)
        if page is not None:
            return paginator.get_paginated_response(OrderSerializer(page, many=True).data)
        return Response(OrderSerializer(orders, many=True).data)

    data = request.data
    items_data = data.get("items", [])
    if not isinstance(items_data, list) or not items_data:
        return Response(
            {"error": "حداقل یک قلم کالا در سفارش لازم است"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    customer_name = str(data.get("customer", "")).strip()
    phone = str(data.get("phone", "")).strip()
    address = str(data.get("address", "")).strip()
    email = str(data.get("email", "")).strip()
    order_status = data.get("status", Order.ORDER_STATUSES[0])
    payment = data.get("payment", Order.PAYMENT_STATUSES[1])
    coupon_code = str(data.get("coupon_code", "")).strip()
    shipping_cost = int(data.get("shipping_cost", 0))
    shipping_method = str(data.get("shipping_method", "پست پیشتاز")).strip()
    customer_notes = str(data.get("customer_notes", "")).strip()

    try:
        order = OrderService.create_order(
            items_data=items_data,
            customer_name=customer_name,
            phone=phone,
            address=address,
            email=email,
            user=request.user if request.user.is_authenticated else None,
            status=order_status,
            payment=payment,
            coupon_code=coupon_code,
            shipping_cost=shipping_cost,
            shipping_method=shipping_method,
            customer_notes=customer_notes,
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="مشاهده یا حذف سفارش با کد یا شناسه")
@api_view(["GET", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def order_detail(request: Any, code: str) -> Response:
    order = Order.objects.filter(code=code).prefetch_related("order_items", "status_history").first()
    if not order and code.isdigit():
        order = Order.objects.filter(id=int(code)).prefetch_related("order_items", "status_history").first()
    if not order:
        return Response({"error": "سفارش یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        order.delete()
        return Response({"success": True})
    return Response(OrderSerializer(order).data)


@extend_schema(summary="به‌روزرسانی وضعیت سفارش")
@api_view(["PATCH"])
@permission_classes([AllowAny])
@csrf_exempt
def order_status(request: Any, code: str) -> Response:
    order = Order.objects.filter(code=code).first()
    if not order and code.isdigit():
        order = Order.objects.filter(id=int(code)).first()
    if not order:
        return Response({"error": "سفارش یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    status_value = request.data.get("status")
    comment = request.data.get("comment", "")
    if not status_value:
        return Response(
            {"error": "مقدار status الزامی است"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        updated = OrderService.update_status(order, status_value, comment=comment)
        return Response(OrderSerializer(updated).data)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="مشاهده تاریخچه تغییرات وضعیت سفارش")
@api_view(["GET"])
@permission_classes([AllowAny])
def order_history(request: Any, code: str) -> Response:
    order = Order.objects.filter(code=code).first()
    if not order and code.isdigit():
        order = Order.objects.filter(id=int(code)).first()
    if not order:
        return Response({"error": "سفارش یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    history = order.status_history.all()
    return Response(OrderStatusHistorySerializer(history, many=True).data)


@extend_schema(summary="مشاهده و چاپ فاکتور رسمی سفارش")
@api_view(["GET"])
@permission_classes([AllowAny])
def order_invoice(request: Any, code: str) -> HttpResponse:
    order = Order.objects.filter(code=code).prefetch_related("order_items").first()
    if not order and code.isdigit():
        order = Order.objects.filter(id=int(code)).prefetch_related("order_items").first()
    if not order:
        return HttpResponse("<h1>سفارش یافت نشد</h1>", status=404)

    setting = SiteSetting.get_settings()
    rows_html = ""
    for i, it in enumerate(order.order_items.all(), 1):
        rows_html += f"""
        <tr>
          <td>{i}</td>
          <td>{it.product_name}</td>
          <td>{it.quantity}</td>
          <td>{it.price:,} تومان</td>
          <td>{it.subtotal:,} تومان</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="fa">
    <head>
      <meta charset="utf-8">
      <title>فاکتور سفارش {order.code}</title>
      <style>
        body {{ font-family: Tahoma, 'Vazirmatn', sans-serif; direction: rtl; background: #f8fafc; padding: 30px 15px; color: #1e293b; }}
        .invoice-card {{ max-width: 800px; margin: auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.06); }}
        .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 25px; }}
        .header h1 {{ margin: 0; font-size: 24px; color: #0284c7; }}
        .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; background: #f1f5f9; padding: 20px; border-radius: 8px; margin-bottom: 25px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; }}
        th, td {{ border: 1px solid #cbd5e1; padding: 12px; text-align: center; }}
        th {{ background: #f8fafc; font-weight: bold; }}
        .totals {{ max-width: 320px; margin-right: auto; background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; }}
        .total-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
        .total-row.final {{ font-size: 18px; font-weight: bold; color: #059669; border-top: 2px solid #cbd5e1; padding-top: 8px; margin-top: 8px; }}
        .print-btn {{ display: block; margin: 30px auto 0; padding: 12px 24px; background: #0284c7; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }}
        @media print {{ .print-btn {{ display: none; }} body {{ background: white; padding: 0; }} .invoice-card {{ box-shadow: none; border: none; padding: 0; }} }}
      </style>
    </head>
    <body>
      <div class="invoice-card">
        <div class="header">
          <div>
            <h1>{setting.title}</h1>
            <p style="margin: 5px 0 0; color: #64748b;">تلفن: {setting.phone_support} | {setting.address}</p>
          </div>
          <div style="text-align: left;">
            <p><strong>شماره فاکتور:</strong> {order.code}</p>
            <p><strong>تاریخ:</strong> {order.date}</p>
          </div>
        </div>

        <div class="info-grid">
          <div><strong>خریدار:</strong> {order.customer}</div>
          <div><strong>شماره تماس:</strong> {order.phone}</div>
          <div><strong>نشانی تحویل:</strong> {order.address}</div>
          <div><strong>وضعیت پرداخت:</strong> {order.payment}</div>
        </div>

        <table>
          <thead>
            <tr>
              <th>ردیف</th>
              <th>نام کالا</th>
              <th>تعداد</th>
              <th>قیمت واحد</th>
              <th>مبلغ کل</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>

        <div class="totals">
          <div class="total-row"><span>مجموع اقلام:</span><span>{order.raw_total:,} تومان</span></div>
          <div class="total-row"><span>هزینه ارسال ({order.shipping_method}):</span><span>{order.shipping_cost:,} تومان</span></div>
          <div class="total-row"><span>تخفیف:</span><span>{order.discount_amount:,} تومان</span></div>
          <div class="total-row final"><span>مبلغ قابل پرداخت:</span><span>{order.total:,} تومان</span></div>
        </div>

        <button class="print-btn" onclick="window.print()">چاپ فاکتور</button>
      </div>
    </body>
    </html>
    """
    return HttpResponse(html)


# ============================================================================
# COUPONS & PROMOTIONS
# ============================================================================

@extend_schema(summary="بررسی و اعتبارسنجی کد تخفیف")
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def coupon_validate(request: Any) -> Response:
    code = request.data.get("code", "")
    total_amount = int(request.data.get("total_amount", 0))

    try:
        res = CouponService.validate_coupon(
            code=code,
            user=request.user if request.user.is_authenticated else None,
            total_amount=total_amount,
        )
        return Response({
            "valid": True,
            "coupon_code": res["coupon_code"],
            "discount_type": res["discount_type"],
            "discount_value": res["discount_value"],
            "discount_amount": res["discount_amount"],
            "final_total": res["final_total"],
            "message": res["message"],
        })
    except ValidationError as exc:
        return Response({"error": str(exc.message), "valid": False}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# PAYMENT GATEWAY
# ============================================================================

@extend_schema(summary="درخواست شروع پرداخت سفارش")
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def payment_request(request: Any) -> Response:
    order_code = request.data.get("order_code") or request.data.get("order_id")
    gateway = request.data.get("gateway", "mock")

    if not order_code:
        return Response({"error": "کد سفارش الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

    order = Order.objects.filter(code=str(order_code)).first()
    if not order and str(order_code).isdigit():
        order = Order.objects.filter(id=int(order_code)).first()
    if not order:
        return Response({"error": "سفارش یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    try:
        result = PaymentService.initiate_payment(
            order=order,
            gateway=gateway,
            user=request.user if request.user.is_authenticated else None,
        )
        return Response(result)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="تأییدیه و بازگشت از درگاه پرداخت")
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def payment_verify(request: Any) -> Response:
    authority = (
        request.query_params.get("Authority")
        or request.data.get("Authority")
        or request.query_params.get("authority")
        or request.data.get("authority")
    )
    status_param = (
        request.query_params.get("Status")
        or request.data.get("Status")
        or request.query_params.get("status")
        or request.data.get("status")
        or "OK"
    )

    if not authority:
        return Response({"error": "توکن پرداخت (Authority) الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = PaymentService.verify_payment(authority=authority, status_param=status_param)
        return Response(result)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


def mock_payment_page(request: Any, authority: str) -> HttpResponse:
    """درگاه پرداخت تستی در محیط توسعه برای شبیه‌سازی پرداخت بدون نیاز به درگاه واقعی"""
    tx = PaymentTransaction.objects.filter(authority=authority).select_related("order").first()
    if not tx:
        return HttpResponse("<h1>تراکنش یافت نشد</h1>", status=404)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "pay":
            res = PaymentService.verify_payment(authority, status_param="OK", card_pan="6037-9912-3456-7890")
            html = f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="fa">
            <head><meta charset="utf-8"><title>پرداخت موفق</title>
            <style>body {{ font-family: sans-serif; text-align: center; padding: 50px; background: #f0fdf4; }}
            .card {{ background: white; max-width: 500px; margin: auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h2 {{ color: #16a34a; }}
            a.btn {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background: #16a34a; color: white; text-decoration: none; border-radius: 8px; }}
            </style></head>
            <body><div class="card">
            <h2>✓ پرداخت با موفقیت انجام شد</h2>
            <p>سفارش: <strong>{tx.order.code}</strong></p>
            <p>مبلغ: <strong>{tx.amount:,} تومان</strong></p>
            <p>کد پیگیری بانکی: <strong>{res.get('ref_id')}</strong></p>
            <a class="btn" href="http://localhost:5173/profile?tab=Orders">بازگشت به سایت فروشگاه</a>
            </div></body></html>
            """
            return HttpResponse(html)
        else:
            PaymentService.verify_payment(authority, status_param="NOK")
            html = f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="fa">
            <head><meta charset="utf-8"><title>انصراف از پرداخت</title>
            <style>body {{ font-family: sans-serif; text-align: center; padding: 50px; background: #fef2f2; }}
            .card {{ background: white; max-width: 500px; margin: auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h2 {{ color: #dc2626; }}
            a.btn {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background: #dc2626; color: white; text-decoration: none; border-radius: 8px; }}
            </style></head>
            <body><div class="card">
            <h2>✗ پرداخت لغو گردید</h2>
            <p>سفارش: <strong>{tx.order.code}</strong></p>
            <a class="btn" href="http://localhost:5173/cart">بازگشت به سبد خرید</a>
            </div></body></html>
            """
            return HttpResponse(html)

    html = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="fa">
    <head><meta charset="utf-8"><title>شبیه‌ساز درگاه پرداخت شاپرک / زرین‌پال</title>
    <style>
    body {{ font-family: Tahoma, sans-serif; background: #f8fafc; padding: 40px 15px; direction: rtl; }}
    .gateway-box {{ max-width: 480px; margin: auto; background: white; border-radius: 16px; border: 1px solid #e2e8f0; padding: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
    .logo {{ font-size: 24px; font-weight: bold; color: #1e293b; text-align: center; margin-bottom: 20px; border-bottom: 1px solid #f1f5f9; padding-bottom: 15px; }}
    .row {{ display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 15px; color: #475569; }}
    .row strong {{ color: #0f172a; }}
    .buttons {{ display: flex; gap: 12px; margin-top: 25px; }}
    .btn {{ flex: 1; padding: 14px; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; font-weight: bold; }}
    .btn-pay {{ background: #10b981; color: white; }}
    .btn-cancel {{ background: #f1f5f9; color: #64748b; }}
    </style></head>
    <body>
    <div class="gateway-box">
      <div class="logo">درگاه پرداخت الکترونیک (محیط تستی آوا)</div>
      <div class="row"><span>پذیرنده:</span><strong>فروشگاه آوای انعکاس</strong></div>
      <div class="row"><span>شماره سفارش:</span><strong>{tx.order.code}</strong></div>
      <div class="row"><span>مبلغ قابل پرداخت:</span><strong>{tx.amount:,} تومان</strong></div>
      <div class="row"><span>کد تراکنش:</span><strong style="direction:ltr;">{tx.authority}</strong></div>
      <form method="POST">
        <div class="buttons">
          <button type="submit" name="action" value="pay" class="btn btn-pay">پرداخت تستی موفق</button>
          <button type="submit" name="action" value="cancel" class="btn btn-cancel">انصراف از پرداخت</button>
        </div>
      </form>
    </div>
    </body></html>
    """
    return HttpResponse(html)


# ============================================================================
# BANNERS & HOMEPAGE SLIDERS
# ============================================================================

@extend_schema(summary="لیست بنرها و اسلایدرهای صفحه اول")
@api_view(["GET"])
@permission_classes([AllowAny])
def banner_list(request: Any) -> Response:
    b_type = request.query_params.get("type")
    qs = Banner.objects.filter(is_active=True)
    if b_type:
        qs = qs.filter(banner_type=b_type)
    return Response(BannerSerializer(qs, many=True, context={"request": request}).data)


# ============================================================================
# CONTACT US & NEWSLETTER & SITE SETTINGS
# ============================================================================

@extend_schema(summary="ارسال پیام تماس با ما")
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def contact_us(request: Any) -> Response:
    serializer = ContactMessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"success": True, "message": "پیام شما با موفقیت ارسال شد. کارشناسان ما به‌زودی با شما تماس خواهند گرفت."}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="عضویت در خبرنامه و دریافت تخفیف‌ها")
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def newsletter_subscribe(request: Any) -> Response:
    val = (request.data.get("email_or_phone") or request.data.get("email") or "").strip()
    if not val:
        return Response({"error": "ایمیل یا شماره تلفن الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

    sub, created = NewsletterSubscriber.objects.get_or_create(email_or_phone=val)
    return Response({"success": True, "message": "عضویت شما در خبرنامه با موفقیت انجام شد."})


@extend_schema(summary="مشاهده تنظیمات و اطلاعات تماس فروشگاه")
@api_view(["GET"])
@permission_classes([AllowAny])
def site_settings_view(request: Any) -> Response:
    settings_obj = SiteSetting.get_settings()
    return Response(SiteSettingSerializer(settings_obj).data)


# ============================================================================
# CUSTOMERS & USER PROFILE
# ============================================================================

@extend_schema(summary="لیست مشتریان برای پنل ادمین")
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def customer_list(request: Any) -> Response:
    customers = User.objects.filter(is_staff=False).order_by("-id")
    paginator = ConditionalPageNumberPagination()
    page = paginator.paginate_queryset(customers, request)
    if page is not None:
        return paginator.get_paginated_response(CustomerSerializer(page, many=True).data)
    return Response(CustomerSerializer(customers, many=True).data)


@extend_schema(summary="مشاهده یا ویرایش پروفایل کاربری")
@api_view(["GET", "PUT"])
@permission_classes([AllowAny])
@csrf_exempt
def profile(request: Any) -> Response:
    if request.method == "GET":
        phone = request.query_params.get("phone", "").strip()
        user = None
        if request.user.is_authenticated:
            user = request.user
        elif phone:
            user = User.objects.filter(phone=phone).first()
        else:
            user = User.objects.filter(is_staff=False).first()

        if not user:
            return Response(
                {
                    "NameAndFamily": "",
                    "BirthDate": "",
                    "IdCard": "",
                    "Email": "",
                    "Number": "",
                    "gender": "",
                    "avatar": None,
                }
            )

        avatar_url = None
        if user.avatar:
            avatar_url = request.build_absolute_uri(user.avatar.url)

        return Response(
            {
                "NameAndFamily": user.name,
                "BirthDate": user.birth_date,
                "IdCard": user.national_code,
                "Email": user.email or "",
                "Number": user.phone,
                "gender": user.gender,
                "avatar": avatar_url,
            }
        )

    serializer = ProfileSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    phone = (data.get("Number") or "").strip()
    name = (data.get("NameAndFamily") or "").strip()
    email = (data.get("Email") or "").strip()
    birth_date = (data.get("BirthDate") or "").strip()
    id_card = (data.get("IdCard") or "").strip()
    gender = (data.get("gender") or "").strip()

    if request.user.is_authenticated:
        target_user = request.user
        if name:
            target_user.name = name
        if email:
            target_user.email = email
        if birth_date:
            target_user.birth_date = birth_date
        if id_card:
            target_user.national_code = id_card
        if gender:
            target_user.gender = gender
        target_user.save()
    elif phone:
        target_user, _ = User.objects.update_or_create(
            phone=phone,
            defaults={
                "name": name or "کاربر",
                "email": email or None,
                "birth_date": birth_date,
                "national_code": id_card,
                "gender": gender,
            },
        )
    elif name:
        target_user = User.objects.filter(name=name).first()
        if target_user:
            target_user.email = email or target_user.email
            target_user.birth_date = birth_date or target_user.birth_date
            target_user.national_code = id_card or target_user.national_code
            target_user.gender = gender or target_user.gender
            target_user.save()

    return Response({**{k: v for k, v in data.items() if v is not None}, "success": True})


@extend_schema(summary="آپلود تصویر آواتار پروفایل کاربر")
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def upload_avatar(request: Any) -> Response:
    avatar_file = request.FILES.get("avatar")
    if not avatar_file:
        return Response({"error": "فایل عکس آواتار الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        phone = request.data.get("phone")
        if phone:
            user = User.objects.filter(phone=phone).first()

    if not user:
        return Response({"error": "کاربر شناسایی نشد"}, status=status.HTTP_401_UNAUTHORIZED)

    user.avatar = avatar_file
    user.save(update_fields=["avatar"])
    url = request.build_absolute_uri(user.avatar.url)
    return Response({"success": True, "avatar": url})


# ============================================================================
# USER NOTIFICATIONS & IN-APP MESSAGES
# ============================================================================

@extend_schema(summary="لیست پیام‌ها و اعلان‌های کاربر")
@api_view(["GET"])
@permission_classes([AllowAny])
def user_notifications(request: Any) -> Response:
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        phone = request.query_params.get("phone")
        if phone:
            user = User.objects.filter(phone=phone).first()

    if not user:
        return Response([])

    notifications = NotificationService.get_user_notifications(user)
    return Response(NotificationSerializer(notifications, many=True).data)


@extend_schema(summary="علامت‌گذاری پیام به عنوان خوانده‌شده")
@api_view(["PATCH"])
@permission_classes([AllowAny])
@csrf_exempt
def mark_notification_read(request: Any, pk: int) -> Response:
    notification = Notification.objects.filter(pk=pk).first()
    if not notification:
        return Response({"error": "پیام یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return Response({"success": True})


@extend_schema(summary="علامت‌گذاری تمام پیام‌های کاربر به عنوان خوانده‌شده")
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def mark_all_notifications_read(request: Any) -> Response:
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        phone = request.data.get("phone")
        if phone:
            user = User.objects.filter(phone=phone).first()

    if not user:
        return Response({"error": "کاربر مشخص نشده است"}, status=status.HTTP_400_BAD_REQUEST)

    Notification.objects.filter(user=user, is_read=False).update(is_read=True)
    return Response({"success": True})


# ============================================================================
# ARTICLES & BLOG
# ============================================================================

@extend_schema(summary="لیست مقالات وبلاگ")
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def article_list(request: Any) -> Response:
    if request.method == "GET":
        articles = Article.objects.all().prefetch_related("article_videos")
        paginator = ConditionalPageNumberPagination()
        page = paginator.paginate_queryset(articles, request)
        if page is not None:
            return paginator.get_paginated_response(
                ArticleSerializer(page, many=True, context={"request": request}).data
            )
        return Response(
            ArticleSerializer(articles, many=True, context={"request": request}).data
        )

    serializer = ArticleSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="جزئیات، ویرایش یا حذف مقاله")
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def article_detail(request: Any, pk: int) -> Response:
    try:
        article = Article.objects.prefetch_related("article_videos").get(pk=pk)
    except Article.DoesNotExist:
        return Response({"error": "مقاله یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(ArticleSerializer(article, context={"request": request}).data)

    if request.method == "DELETE":
        article.delete()
        return Response({"success": True})

    serializer = ArticleSerializer(
        article,
        data=request.data,
        partial=(request.method == "PATCH"),
        context={"request": request},
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# AUTHENTICATION (OTP)
# ============================================================================

@extend_schema(summary="ارسال کد تأیید ورود/ثبت‌نام به شماره موبایل")
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OtpRateThrottle])
@csrf_exempt
def send_code(request: Any) -> Response:
    phone = request.data.get("phone", "")
    try:
        result = AuthService.request_otp(phone)
        return Response(result)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="بررسی کد تأیید و صدور توکن‌های JWT")
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OtpVerifyRateThrottle])
@csrf_exempt
def verify_code(request: Any) -> Response:
    phone = request.data.get("phone", "")
    code = request.data.get("code", "")
    session_key = (
        (request.session.session_key if hasattr(request, "session") else None)
        or request.data.get("session_key")
    )

    try:
        auth_data = AuthService.verify_otp(phone, code, session_key=session_key)
        user = auth_data["user"]
        return Response(
            {
                "success": True,
                "tokens": auth_data["tokens"],
                "customer": CustomerSerializer(user).data,
            }
        )
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# SHOPPING CART
# ============================================================================

def get_request_cart(request: Any):
    user = request.user if request.user.is_authenticated else None
    session_key = (
        request.headers.get("X-Session-Key")
        or request.query_params.get("session_key")
        or (request.session.session_key if hasattr(request, "session") else None)
    )
    if not user and not session_key:
        if hasattr(request, "session") and not request.session.session_key:
            request.session.create()
        session_key = getattr(request.session, "session_key", None)
    return CartService.get_or_create_cart(user=user, session_key=session_key)


@extend_schema(summary="مشاهده یا خالی کردن سبد خرید")
@api_view(["GET", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def cart_view(request: Any) -> Response:
    cart = get_request_cart(request)
    if request.method == "DELETE":
        CartService.clear_cart(cart)
        return Response({"success": True})

    summary = CartService.get_cart_summary(cart, request=request)
    return Response(summary)


@extend_schema(summary="افزودن کالا به سبد خرید")
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def cart_add_item(request: Any) -> Response:
    cart = get_request_cart(request)
    product_id = request.data.get("product_id")
    quantity = int(request.data.get("quantity", 1))

    if not product_id:
        return Response(
            {"error": "شناسه محصول الزامی است"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        CartService.add_item(cart, product_id=int(product_id), quantity=quantity)
        summary = CartService.get_cart_summary(cart, request=request)
        return Response(summary, status=status.HTTP_201_CREATED)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="تغییر تعداد یا حذف یک کالا از سبد خرید")
@api_view(["PATCH", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def cart_item_detail(request: Any, product_id: int) -> Response:
    cart = get_request_cart(request)
    if request.method == "DELETE":
        CartService.remove_item(cart, product_id=product_id)
        summary = CartService.get_cart_summary(cart, request=request)
        return Response(summary)

    quantity = int(request.data.get("quantity", 1))
    try:
        CartService.update_item(cart, product_id=product_id, quantity=quantity)
        summary = CartService.get_cart_summary(cart, request=request)
        return Response(summary)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="اعمال یا حذف کد تخفیف در سبد خرید")
@api_view(["POST", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def cart_apply_coupon(request: Any) -> Response:
    cart = get_request_cart(request)
    if request.method == "DELETE":
        CartService.remove_coupon(cart)
        summary = CartService.get_cart_summary(cart, request=request)
        return Response(summary)

    code = request.data.get("code", "")
    try:
        CartService.apply_coupon(cart, code=code, user=request.user if request.user.is_authenticated else None)
        summary = CartService.get_cart_summary(cart, request=request)
        return Response(summary)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="تسویه حساب و تبدیل سبد خرید به سفارش نهایی")
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([OrderCreateRateThrottle])
@csrf_exempt
def cart_checkout(request: Any) -> Response:
    cart = get_request_cart(request)
    customer_name = request.data.get("customer", "")
    phone = request.data.get("phone", "")
    address = request.data.get("address", "")
    email = request.data.get("email", "")
    coupon_code = request.data.get("coupon_code", "")
    shipping_method = request.data.get("shipping_method", "پست پیشتاز")
    customer_notes = request.data.get("customer_notes", "")

    if not customer_name and request.user.is_authenticated:
        customer_name = request.user.name or request.user.phone
    if not phone and request.user.is_authenticated:
        phone = request.user.phone

    try:
        order = OrderService.checkout_cart(
            cart=cart,
            customer_name=customer_name,
            phone=phone,
            address=address,
            email=email,
            user=request.user if request.user.is_authenticated else None,
            coupon_code=coupon_code,
            shipping_method=shipping_method,
            customer_notes=customer_notes,
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# USER ORDERS (PROFILE)
# ============================================================================

@extend_schema(summary="لیست سفارش‌های کاربر دسته‌بندی‌شده بر اساس وضعیت")
@api_view(["GET"])
@permission_classes([AllowAny])
def user_orders(request: Any) -> Response:
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        phone = request.query_params.get("phone", "").strip()
        if phone:
            user = User.objects.filter(phone=phone).first()

    if not user:
        return Response(
            {"InProgress": [], "Delivered": [], "Returned": [], "Canceled": []}
        )

    orders = Order.objects.filter(
        Q(user=user) | Q(phone=user.phone) | Q(customer__iexact=user.name)
    ).prefetch_related("order_items", "status_history")

    status_mapping = {
        "در انتظار پردازش": "InProgress",
        "در حال ارسال": "InProgress",
        "تحویل شده": "Delivered",
        "مرجوع شده": "Returned",
        "بازگشت وجه": "Returned",
        "لغو شده": "Canceled",
    }

    result = {
        "InProgress": [],
        "Delivered": [],
        "Returned": [],
        "Canceled": [],
    }

    for o in orders:
        category_key = status_mapping.get(o.status, "InProgress")
        result[category_key].append(OrderSerializer(o).data)

    return Response(result)


# ============================================================================
# ADDRESSES
# ============================================================================

@extend_schema(summary="لیست یا ایجاد آدرس‌های کاربر")
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def address_list(request: Any) -> Response:
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        phone = request.query_params.get("phone") or request.data.get("phone")
        if phone:
            user = User.objects.filter(phone=phone).first()

    if request.method == "GET":
        if not user:
            return Response([])
        addresses = Address.objects.filter(user=user)
        return Response(AddressSerializer(addresses, many=True).data)

    if not user:
        return Response(
            {"error": "کاربر مشخص نشده است"}, status=status.HTTP_400_BAD_REQUEST
        )

    serializer = AddressSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="حذف یا پیش‌فرض کردن آدرس")
@api_view(["DELETE", "PATCH"])
@permission_classes([AllowAny])
@csrf_exempt
def address_detail(request: Any, pk: int) -> Response:
    address = Address.objects.filter(pk=pk).first()
    if not address:
        return Response({"error": "آدرس یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        address.delete()
        return Response({"success": True})

    Address.objects.filter(user=address.user).update(is_default=False)
    address.is_default = True
    address.save(update_fields=["is_default"])
    return Response(AddressSerializer(address).data)


# ============================================================================
# FAVORITES (WISHLIST)
# ============================================================================

@extend_schema(summary="مشاهده یا مدیریت لیست علاقه‌مندی‌ها")
@api_view(["GET", "POST", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def favorite_view(request: Any, product_id: int | None = None) -> Response:
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        phone = request.query_params.get("phone") or request.data.get("phone")
        if phone:
            user = User.objects.filter(phone=phone).first()

    if not user:
        return Response(
            {"error": "احراز هویت کاربر الزامی است"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if request.method == "GET":
        favs = (
            Favorite.objects.filter(user=user)
            .select_related("product")
            .prefetch_related("product__product_images")
        )
        products = [f.product for f in favs]
        return Response(
            ProductSerializer(products, many=True, context={"request": request}).data
        )

    if not product_id:
        product_id = request.data.get("product_id")

    if not product_id:
        return Response(
            {"error": "شناسه محصول الزامی است"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return Response({"error": "محصول یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        Favorite.objects.filter(user=user, product=product).delete()
        return Response({"success": True})

    fav, created = Favorite.objects.get_or_create(user=user, product=product)
    return Response(
        {"success": True, "favorited": True},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


# ============================================================================
# ANALYTICS (ADMIN DASHBOARD)
# ============================================================================

@extend_schema(summary="آمار و شاخص‌های تحلیلی برای داشبورد ادمین")
@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_metrics(request: Any) -> Response:
    metrics = AnalyticsService.get_dashboard_metrics()
    return Response(metrics)
