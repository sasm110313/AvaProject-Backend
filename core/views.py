from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.models import Address, Article, Favorite, Order, Product, User
from core.serializers import (
    AddressSerializer,
    ArticleSerializer,
    CartSerializer,
    CustomerSerializer,
    FavoriteSerializer,
    OrderSerializer,
    ProductSerializer,
    ProfileSerializer,
)
from core.services.analytics_service import AnalyticsService
from core.services.auth_service import AuthService
from core.services.cart_service import CartService
from core.services.order_service import OrderService
from core.services.product_service import ProductService

CATEGORIES = [
    "اسپیکر",
    "هدفون",
    "آمپلی‌فایر",
    "میکروفون",
    "میکسر",
    "کابل و اتصالات",
]


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def product_list(request: Any) -> Response:
    if request.method == "GET":
        category = request.query_params.get("category")
        search = request.query_params.get("search")
        products = ProductService.list_products(category=category, search=search)
        serializer = ProductSerializer(products, many=True, context={"request": request})
        return Response(serializer.data)

    serializer = ProductSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def product_detail(request: Any, pk: int) -> Response:
    try:
        product = ProductService.get_product(product_id=pk)
    except Product.DoesNotExist:
        return Response({"error": "محصول یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ProductSerializer(product, context={"request": request})
        return Response(serializer.data)

    if request.method == "DELETE":
        product.delete()
        return Response({"success": True})

    serializer = ProductSerializer(
        product, data=request.data, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def order_list(request: Any) -> Response:
    if request.method == "GET":
        orders = Order.objects.all().prefetch_related("order_items")
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
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "DELETE"])
@permission_classes([AllowAny])
@csrf_exempt
def order_detail(request: Any, code: str) -> Response:
    order = Order.objects.filter(code=code).first()
    if not order and code.isdigit():
        order = Order.objects.filter(id=int(code)).first()
    if not order:
        return Response({"error": "سفارش یافت نشد"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "DELETE":
        order.delete()
        return Response({"success": True})
    return Response(OrderSerializer(order).data)


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
    if not status_value:
        return Response(
            {"error": "مقدار status الزامی است"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        updated = OrderService.update_status(order, status_value)
        return Response(OrderSerializer(updated).data)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def customer_list(request: Any) -> Response:
    customers = User.objects.filter(is_staff=False).order_by("-id")
    return Response(CustomerSerializer(customers, many=True).data)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@csrf_exempt
def article_list(request: Any) -> Response:
    if request.method == "GET":
        articles = Article.objects.all().prefetch_related("article_videos")
        return Response(
            ArticleSerializer(articles, many=True, context={"request": request}).data
        )

    serializer = ArticleSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
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
        article, data=request.data, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def category_list(request: Any) -> Response:
    db_categories = list(
        Product.objects.values_list("category", flat=True).distinct()
    )
    all_categories = sorted(list(set(CATEGORIES + [c for c in db_categories if c])))
    return Response(all_categories)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def send_code(request: Any) -> Response:
    phone = request.data.get("phone", "")
    try:
        result = AuthService.request_otp(phone)
        return Response(result)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def verify_code(request: Any) -> Response:
    phone = request.data.get("phone", "")
    code = request.data.get("code", "")
    session_key = request.session.session_key or request.data.get("session_key")

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
                }
            )

        return Response(
            {
                "NameAndFamily": user.name,
                "BirthDate": user.birth_date,
                "IdCard": user.national_code,
                "Email": user.email or "",
                "Number": user.phone,
                "gender": user.gender,
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


def get_request_cart(request: Any):
    user = request.user if request.user.is_authenticated else None
    session_key = (
        request.headers.get("X-Session-Key")
        or request.query_params.get("session_key")
        or request.session.session_key
    )
    if not user and not session_key:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
    return CartService.get_or_create_cart(user=user, session_key=session_key)


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


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def cart_checkout(request: Any) -> Response:
    cart = get_request_cart(request)
    customer_name = request.data.get("customer", "")
    phone = request.data.get("phone", "")
    address = request.data.get("address", "")
    email = request.data.get("email", "")

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
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    except ValidationError as exc:
        return Response({"error": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_metrics(request: Any) -> Response:
    metrics = AnalyticsService.get_dashboard_metrics()
    return Response(metrics)


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
    ).prefetch_related("order_items")

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