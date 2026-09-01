import random

from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .jalali import today_jalali
from .models import Order, OtpCode, Product, Customer, Article
from .serializers import (
    ArticleSerializer,
    CustomerSerializer,
    OrderSerializer,
    ProductSerializer,
    ProfileSerializer,
)

CATEGORIES = [
    "اسپیکر",
    "هدفون",
    "آمپلی\u200cفایر",
    "میکروفون",
    "میکسر",
    "کابل و اتصالات",
]


@api_view(["GET", "POST"])
@csrf_exempt
def product_list(request):
    if request.method == "GET":
        products = Product.objects.all()
        return Response(
            ProductSerializer(products, many=True, context={"request": request}).data
        )
    serializer = ProductSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["GET", "PUT", "DELETE"])
@csrf_exempt
def product_detail(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "محصول یافت نشد"}, status=404)
    if request.method == "GET":
        return Response(ProductSerializer(product, context={"request": request}).data)
    if request.method == "DELETE":
        product.delete()
        return Response({"success": True})
    serializer = ProductSerializer(
        product, data=request.data, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(["GET", "POST"])
@csrf_exempt
def order_list(request):
    if request.method == "GET":
        orders = Order.objects.all()
        return Response(OrderSerializer(orders, many=True).data)
    return order_create(request)


def order_create(request):
    data = request.data
    items_data = data.get("items", [])
    if not isinstance(items_data, list) or not items_data:
        return Response({"error": "حداقل یک قلم کالا لازم است"}, status=400)
    products = {item["product_id"]: item.get("quantity", 1) for item in items_data if isinstance(item, dict)}
    if not products:
        return Response({"error": "اطلاعات اقلام نامعتبر است"}, status=400)
    existing = Product.objects.filter(id__in=products.keys())
    if existing.count() != len(products):
        return Response({"error": "برخی محصولات یافت نشدند"}, status=400)
    codes = [int(x[len("ORD-"):]) for x in Order.objects.values_list("code", flat=True) if x.startswith("ORD-")]
    next_code = (max(codes) + 1) if codes else 1
    order = Order.objects.create(
        code=f"ORD-{next_code:04d}",
        customer=data.get("customer", ""),
        phone=data.get("phone", ""),
        email=data.get("email", ""),
        address=data.get("address", ""),
        date=today_jalali(),
        status=data.get("status", Order.ORDER_STATUSES[0]),
        payment=data.get("payment", Order.PAYMENT_STATUSES[1]),
    )
    for product in existing:
        order.items.create(
            product=product,
            product_name=product.name,
            price=product.price,
            quantity=products[product.id],
        )
    return Response(OrderSerializer(order).data, status=201)


@api_view(["GET"])
@csrf_exempt
def order_detail(request, code):
    try:
        order = Order.objects.get(code=code)
    except Order.DoesNotExist:
        return Response({"error": "سفارش یافت نشد"}, status=404)
    return Response(OrderSerializer(order).data)


@api_view(["PATCH"])
@csrf_exempt
def order_status(request, code):
    try:
        order = Order.objects.get(code=code)
    except Order.DoesNotExist:
        return Response({"error": "سفارش یافت نشد"}, status=404)
    status_value = request.data.get("status")
    if not status_value:
        return Response({"error": "مقدار status الزامی است"}, status=400)
    if status_value not in Order.ORDER_STATUSES:
        return Response({"error": "مقدار status نامعتبر است"}, status=400)
    order.status = status_value
    order.save()
    return Response(OrderSerializer(order).data)


@api_view(["GET"])
@csrf_exempt
def customer_list(request):
    customers = Customer.objects.all()
    return Response(CustomerSerializer(customers, many=True).data)


@api_view(["GET", "POST"])
@csrf_exempt
def article_list(request):
    if request.method == "GET":
        articles = Article.objects.all()
        return Response(
            ArticleSerializer(articles, many=True, context={"request": request}).data
        )
    serializer = ArticleSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["GET", "PUT", "DELETE"])
@csrf_exempt
def article_detail(request, pk):
    try:
        article = Article.objects.get(pk=pk)
    except Article.DoesNotExist:
        return Response({"error": "مقاله یافت نشد"}, status=404)
    if request.method == "GET":
        return Response(ArticleSerializer(article, context={"request": request}).data)
    if request.method == "DELETE":
        article.delete()
        return Response({"success": True})
    serializer = ArticleSerializer(
        article, data=request.data, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@csrf_exempt
def category_list(request):
    return Response(CATEGORIES)


@api_view(["POST"])
@csrf_exempt
def send_code(request):
    phone = request.data.get("phone", "").strip()
    if len(phone) < 10:
        return Response({"error": "شماره موبایل نامعتبر است"}, status=400)
    OtpCode.objects.filter(phone=phone).delete()
    code = str(random.randint(10000, 99999))
    OtpCode.objects.create(phone=phone, code=code)
    return Response({"success": True, "devCode": code})


@api_view(["POST"])
@csrf_exempt
def verify_code(request):
    phone = request.data.get("phone", "").strip()
    code = request.data.get("code", "").strip()
    otp = OtpCode.objects.filter(phone=phone, code=code).order_by("-id").first()
    if not otp:
        return Response({"error": "کد وارد شده صحیح نیست"}, status=400)
    otp.delete()
    customer, _ = Customer.objects.get_or_create(phone=phone, defaults={"name": "کاربر"})
    return Response(
        {"success": True, "customer": CustomerSerializer(customer).data}
    )


@api_view(["GET", "PUT"])
@csrf_exempt
def profile(request):
    if request.method == "GET":
        phone = request.query_params.get("phone", "").strip()
        customer = None
        if phone:
            customer = Customer.objects.filter(phone=phone).first()
        else:
            customer = Customer.objects.first()
        if not customer:
            return Response(
                {"NameAndFamily": "", "BirthDate": "", "IdCard": "", "Email": "", "Number": "", "gender": ""}
            )
        return Response(
            {
                "NameAndFamily": customer.name,
                "BirthDate": "",
                "IdCard": "",
                "Email": customer.email,
                "Number": customer.phone,
                "gender": "",
            }
        )
    serializer = ProfileSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    data = serializer.validated_data
    phone = (data.get("Number") or "").strip()
    name = (data.get("NameAndFamily") or "").strip()
    defaults = {"email": data.get("Email", "")}
    if phone:
        Customer.objects.update_or_create(phone=phone, defaults={**defaults, "name": name or "کاربر"})
    elif name:
        Customer.objects.update_or_create(name=name, defaults=defaults)
    return Response({**{k: v for k, v in data.items() if v is not None}, "success": True})