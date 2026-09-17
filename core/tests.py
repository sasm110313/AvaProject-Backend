import json
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Article, Order, OtpCode, Product, User
from core.services.auth_service import AuthService
from core.services.cart_service import CartService
from core.services.order_service import OrderService

TINY_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


def make_product(sku="TESTSKU1", stock=5, price=1000000):
    return Product.objects.create(
        name="محصول تست",
        category="اسپیکر",
        sku=sku,
        price=price,
        stock=stock,
        threshold=2,
    )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProductApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_product_list(self):
        make_product()
        response = self.client.get("/api/products")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["status"], "فعال")

    def test_create_update_delete_product_with_files(self):
        image = SimpleUploadedFile("a.png", TINY_PNG, content_type="image/png")
        video = SimpleUploadedFile("a.mp4", b"FAKEMP4", content_type="video/mp4")
        payload = {
            "name": "محصول جدید",
            "category": "میکروفون",
            "sku": "NEWSKU",
            "price": "2000000",
            "stock": "3",
            "threshold": "2",
            "images": [image],
            "video": video,
        }
        created = self.client.post("/api/products", payload, format="multipart")
        self.assertEqual(created.status_code, 201, created.content)
        data = created.json()
        self.assertEqual(data["sku"], "NEWSKU")
        self.assertEqual(len(data["images"]), 1)
        self.assertIsNotNone(data["video"])

        image_id = data["images"][0]["id"]
        keep_url = data["images"][0]["url"]
        new_image = SimpleUploadedFile("b.png", TINY_PNG, content_type="image/png")
        updated_payload = {
            "name": "محصول ویرایش",
            "category": "میکروفون",
            "sku": "NEWSKU",
            "price": "2500000",
            "stock": "0",
            "threshold": "2",
            "existingImageUrls": json.dumps([keep_url]),
            "images": [new_image],
        }
        updated = self.client.put(
            f"/api/products/{data['id']}", updated_payload, format="multipart"
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        updated_data = updated.json()
        self.assertEqual(updated_data["status"], "ناموجود")
        self.assertIsNone(updated_data["video"])
        self.assertEqual(len(updated_data["images"]), 2)
        self.assertEqual(updated_data["images"][0]["id"], image_id)

        deleted = self.client.delete(f"/api/products/{data['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json(), {"success": True})
        self.assertFalse(Product.objects.filter(id=data["id"]).exists())
        self.assertEqual(Product.objects.count(), 0)

    def test_duplicate_sku_rejected(self):
        payload = {
            "name": "اول",
            "category": "اسپیکر",
            "sku": "DUP",
            "price": "1000",
            "stock": "1",
            "threshold": "1",
        }
        self.assertEqual(self.client.post("/api/products", payload).status_code, 201)
        bad = self.client.post(
            "/api/products",
            {
                "name": "دوم",
                "category": "اسپیکر",
                "sku": "DUP",
                "price": "2000",
                "stock": "1",
                "threshold": "1",
            },
        )
        self.assertEqual(bad.status_code, 400)


class OrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_order_deducts_stock(self):
        p1 = make_product("SKU-A", stock=10, price=1000)
        p2 = make_product("SKU-B", stock=5, price=2000)
        payload = {
            "customer": "مشتری اول",
            "phone": "09121234567",
            "status": "در حال ارسال",
            "payment": "پرداخت شده",
            "items": [
                {"product_id": p1.id, "quantity": 2},
                {"product_id": p2.id, "quantity": 1},
            ],
        }
        response = self.client.post("/api/orders", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["customer"], "مشتری اول")
        self.assertEqual(data["items"], 3)
        self.assertEqual(data["total"], 4000)
        self.assertEqual(data["status"], "در حال ارسال")

        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.stock, 8)
        self.assertEqual(p2.stock, 4)

    def test_create_order_insufficient_stock_fails(self):
        p = make_product("SKU-LOW", stock=1)
        payload = {
            "customer": "مشتری",
            "items": [{"product_id": p.id, "quantity": 3}],
        }
        response = self.client.post("/api/orders", payload, format="json")
        self.assertEqual(response.status_code, 400)
        p.refresh_from_db()
        self.assertEqual(p.stock, 1)

    def test_order_status_patch_and_inventory_restoration(self):
        p = make_product("SKU-RESTORE", stock=5)
        order = OrderService.create_order(
            items_data=[{"product_id": p.id, "quantity": 2}],
            customer_name="تست",
        )
        p.refresh_from_db()
        self.assertEqual(p.stock, 3)

        res = self.client.patch(
            f"/api/orders/{order.code}/status",
            {"status": "لغو شده"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.stock, 5)


class CustomerApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_customer_list_returns_unified_metrics(self):
        u = User.objects.create_user(phone="09120000001", name="کاربر تستی")
        p = make_product("SKU-CUST", stock=10, price=50000)
        OrderService.create_order(
            items_data=[{"product_id": p.id, "quantity": 2}],
            customer_name=u.name,
            phone=u.phone,
            user=u,
            payment="پرداخت شده",
        )
        res = self.client.get("/api/customers")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "کاربر تستی")
        self.assertEqual(data[0]["orders"], 1)
        self.assertEqual(data[0]["spent"], 100000)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ArticleApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_article_crud(self):
        cover = SimpleUploadedFile("c.png", TINY_PNG, content_type="image/png")
        video = SimpleUploadedFile("v.mp4", b"VIDEO", content_type="video/mp4")
        payload = {
            "title": "مقاله جدید",
            "excerpt": "خلاصه",
            "content": "متن",
            "category": "آموزشی",
            "author": "نویسنده",
            "status": "منتشر شده",
            "coverImage": cover,
            "videos": [video],
        }
        res = self.client.post("/api/articles", payload, format="multipart")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["title"], "مقاله جدید")
        self.assertEqual(len(data["videos"]), 1)

        list_res = self.client.get("/api/articles")
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.json()), 1)

        del_res = self.client.delete(f"/api/articles/{data['id']}")
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(Article.objects.count(), 0)


@override_settings(DEBUG=True)
class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_send_and_verify_otp_returns_jwt(self):
        res1 = self.client.post("/api/auth/send-code", {"phone": "09127778899"}, format="json")
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.json()["success"])
        dev_code = res1.json().get("devCode")
        self.assertIsNotNone(dev_code)

        res2 = self.client.post(
            "/api/auth/verify-code",
            {"phone": "09127778899", "code": dev_code},
            format="json",
        )
        self.assertEqual(res2.status_code, 200)
        data = res2.json()
        self.assertTrue(data["success"])
        self.assertIn("tokens", data)
        self.assertIn("access", data["tokens"])
        self.assertIn("refresh", data["tokens"])
        self.assertIn("customer", data)
        self.assertEqual(data["customer"]["phone"], "09127778899")

    def test_verify_wrong_code_fails(self):
        AuthService.request_otp("09121112233")
        res = self.client.post(
            "/api/auth/verify-code",
            {"phone": "09121112233", "code": "00000"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)


class CartApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = make_product("SKU-CART", stock=10, price=20000)

    def test_cart_workflow(self):
        add_res = self.client.post(
            "/api/cart/items",
            {"product_id": self.product.id, "quantity": 2},
            format="json",
            HTTP_X_SESSION_KEY="guest-sess-1",
        )
        self.assertEqual(add_res.status_code, 201)
        data = add_res.json()
        self.assertEqual(data["total_items"], 2)
        self.assertEqual(data["total_price"], 40000)

        patch_res = self.client.patch(
            f"/api/cart/items/{self.product.id}",
            {"quantity": 4},
            format="json",
            HTTP_X_SESSION_KEY="guest-sess-1",
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["total_items"], 4)

        checkout_res = self.client.post(
            "/api/cart/checkout",
            {
                "customer": "خریدار مهمان",
                "phone": "09129990011",
                "address": "تهران",
            },
            format="json",
            HTTP_X_SESSION_KEY="guest-sess-1",
        )
        self.assertEqual(checkout_res.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 6)

        cart_check = self.client.get(
            "/api/cart", HTTP_X_SESSION_KEY="guest-sess-1"
        )
        self.assertEqual(cart_check.json()["total_items"], 0)

    def test_cart_merge_on_login(self):
        user = User.objects.create_user(phone="09123334455", name="کاربر لاگین")
        guest_cart = CartService.get_or_create_cart(session_key="guest-sess-2")
        CartService.add_item(guest_cart, self.product.id, quantity=2)

        merged_cart = CartService.merge_guest_cart(user=user, session_key="guest-sess-2")
        self.assertEqual(merged_cart.user, user)
        self.assertEqual(merged_cart.total_items, 2)


class DashboardAnalyticsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_analytics_metrics(self):
        p = make_product("SKU-DASH", stock=1, price=10000)
        OrderService.create_order(
            items_data=[{"product_id": p.id, "quantity": 1}],
            customer_name="داشبورد",
            payment="پرداخت شده",
            status="تحویل شده",
        )
        res = self.client.get("/api/admin/dashboard/metrics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("summary", data)
        self.assertIn("orders_by_status", data)
        self.assertIn("low_stock_alerts", data)
        self.assertIn("recent_orders", data)
        self.assertIn("sales_trend", data)
        self.assertGreaterEqual(data["summary"]["total_revenue"], 10000)


class UserFeaturesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(phone="09121239999", name="کاربر تست ویژگی")
        self.client.force_authenticate(user=self.user)
        self.product = make_product("SKU-FEAT", stock=5, price=30000)

    def test_user_addresses(self):
        res = self.client.post(
            "/api/addresses",
            {"title": "منزل", "address": "تهران میدان ونک", "postal_code": "12345"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        addr_id = res.json()["id"]

        list_res = self.client.get("/api/addresses")
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.json()), 1)

        del_res = self.client.delete(f"/api/addresses/{addr_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(self.client.get("/api/addresses").json(), [])

    def test_user_favorites(self):
        fav_res = self.client.post(f"/api/favorites/{self.product.id}")
        self.assertEqual(fav_res.status_code, 201)
        self.assertTrue(fav_res.json()["favorited"])

        list_favs = self.client.get("/api/favorites")
        self.assertEqual(list_favs.status_code, 200)
        self.assertEqual(len(list_favs.json()), 1)
        self.assertEqual(list_favs.json()[0]["id"], self.product.id)

        del_fav = self.client.delete(f"/api/favorites/{self.product.id}")
        self.assertEqual(del_fav.status_code, 200)
        self.assertEqual(len(self.client.get("/api/favorites").json()), 0)

    def test_user_orders_categorized(self):
        OrderService.create_order(
            items_data=[{"product_id": self.product.id, "quantity": 1}],
            customer_name=self.user.name,
            phone=self.user.phone,
            user=self.user,
            status="در حال ارسال",
        )
        res = self.client.get("/api/me/orders")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("InProgress", data)
        self.assertIn("Delivered", data)
        self.assertEqual(len(data["InProgress"]), 1)
        self.assertEqual(len(data["Delivered"]), 0)