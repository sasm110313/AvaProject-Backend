# Backend Overhaul Design: Core Subsystems & Service Layer Architecture

## 1. Overview
This design outlines the complete backend architecture for the "Ava" e-commerce platform. It transitions the application to a production-grade Django architecture with a clean Service Layer, concurrency-safe inventory and checkout, a unified Custom User/Customer model with OTP and JWT authentication, complete Cart management, and Admin Dashboard analytics. All changes strictly preserve backward compatibility with the existing frontend API contract.

## 2. Guiding Principles & Constraints
- **Zero Frontend Changes**: No file in `Front/` will be altered. All existing API routes, request structures (including `multipart/form-data`), and response keys remain 100% contract-compatible.
- **Clean Code & Zero Explanatory Comments**: Code is written following senior backend engineering standards. Explanatory comments are strictly omitted in favor of expressive naming, explicit types, and clean structure.
- **Clean Service Layer**: Views and serializers remain thin; orchestration, transaction boundaries, stock management, and calculations reside in dedicated domain services.
- **Concurrency Safety**: Stock verification and decrements utilize row-level locking (`select_for_update`) within atomic database transactions to prevent race conditions during high-concurrency checkout.

## 3. Data Models & Database Design

### 3.1 Unified Custom User (`core.User`)
Replaces Django's default user model (`AUTH_USER_MODEL = "core.User"`).
- `id`: BigAutoField (Primary Key)
- `phone`: CharField(max_length=20, unique=True, db_index=True)
- `name`: CharField(max_length=255, blank=True)
- `email`: EmailField(blank=True, null=True)
- `national_code`: CharField(max_length=10, blank=True)
- `birth_date`: CharField(max_length=20, blank=True)
- `gender`: CharField(max_length=10, blank=True)
- `is_staff`: BooleanField(default=False)
- `is_active`: BooleanField(default=True)
- `created_at`: DateTimeField(auto_now_add=True)
- `updated_at`: DateTimeField(auto_now=True)

Includes a custom `UserManager` handling both phone-based user creation and CLI/admin `createsuperuser`.

### 3.2 Address (`core.Address`)
- `user`: ForeignKey(User, on_delete=CASCADE, related_name="addresses")
- `title`: CharField(max_length=100, default="خانه")
- `address`: TextField()
- `postal_code`: CharField(max_length=20, blank=True)
- `is_default`: BooleanField(default=False)

### 3.3 OTP Code (`core.OtpCode`)
- `phone`: CharField(max_length=20, db_index=True)
- `code`: CharField(max_length=10)
- `failed_attempts`: IntegerField(default=0)
- `created_at`: DateTimeField(auto_now_add=True)

### 3.4 Products & Media (`core.Product`, `core.ProductImage`)
- `Product`:
  - `name`: CharField(max_length=255)
  - `category`: CharField(max_length=100, db_index=True)
  - `sku`: CharField(max_length=100, unique=True, db_index=True)
  - `price`: BigIntegerField(validators=[MinValueValidator(1)])
  - `stock`: IntegerField(default=0, validators=[MinValueValidator(0)])
  - `threshold`: IntegerField(default=5, validators=[MinValueValidator(0)])
  - `video`: FileField(upload_to="products/videos/", null=True, blank=True)
  - `created_at`: DateTimeField(auto_now_add=True)
  - `updated_at`: DateTimeField(auto_now=True)
- `ProductImage`:
  - `product`: ForeignKey(Product, on_delete=CASCADE, related_name="product_images")
  - `image`: FileField(upload_to="products/images/")
  - `original_name`: CharField(max_length=255, blank=True)
  - `created_at`: DateTimeField(auto_now_add=True)

### 3.5 Cart Subsystem (`core.Cart`, `core.CartItem`)
- `Cart`:
  - `user`: ForeignKey(User, on_delete=CASCADE, null=True, blank=True, related_name="carts")
  - `session_key`: CharField(max_length=64, null=True, blank=True, db_index=True)
  - `created_at`: DateTimeField(auto_now_add=True)
  - `updated_at`: DateTimeField(auto_now=True)
- `CartItem`:
  - `cart`: ForeignKey(Cart, on_delete=CASCADE, related_name="items")
  - `product`: ForeignKey(Product, on_delete=CASCADE)
  - `quantity`: IntegerField(default=1, validators=[MinValueValidator(1)])
  - Meta: unique_together = ("cart", "product")

### 3.6 Orders & Checkout (`core.Order`, `core.OrderItem`)
- `Order`:
  - `code`: CharField(max_length=30, unique=True, db_index=True)
  - `user`: ForeignKey(User, on_delete=SET_NULL, null=True, blank=True, related_name="orders")
  - `customer`: CharField(max_length=255, db_index=True)
  - `phone`: CharField(max_length=20, blank=True, db_index=True)
  - `email`: CharField(max_length=255, blank=True)
  - `address`: TextField(blank=True)
  - `date`: CharField(max_length=20)
  - `status`: CharField(max_length=50, default="در انتظار پردازش", db_index=True)
  - `payment`: CharField(max_length=50, default="در انتظار", db_index=True)
  - `created_at`: DateTimeField(auto_now_add=True)
- `OrderItem`:
  - `order`: ForeignKey(Order, on_delete=CASCADE, related_name="order_items")
  - `product`: ForeignKey(Product, on_delete=SET_NULL, null=True, blank=True)
  - `product_name`: CharField(max_length=255)
  - `price`: BigIntegerField(validators=[MinValueValidator(1)])
  - `quantity`: IntegerField(default=1, validators=[MinValueValidator(1)])

### 3.7 Articles (`core.Article`, `core.ArticleVideo`)
Maintained for CMS/Blog functionality with full file and video relationship preservation.

## 4. Service Layer Specifications

### 4.1 `AuthService` (`core/services/auth_service.py`)
- `request_otp(phone: str) -> dict`
- `verify_otp(phone: str, code: str, session_key: str | None = None) -> tuple[User, dict]`

### 4.2 `CartService` (`core/services/cart_service.py`)
- `get_or_create_cart(user: User | None, session_key: str | None) -> Cart`
- `add_item(cart: Cart, product_id: int, quantity: int = 1) -> CartItem`
- `update_item(cart: Cart, product_id: int, quantity: int) -> CartItem | None`
- `remove_item(cart: Cart, product_id: int) -> None`
- `clear_cart(cart: Cart) -> None`
- `merge_guest_cart(user: User, session_key: str) -> None`
- `get_cart_summary(cart: Cart) -> dict`

### 4.3 `OrderService` (`core/services/order_service.py`)
- `create_order(user: User | None, customer_name: str, phone: str, address: str, email: str, items_data: list[dict], payment: str = "در انتظار") -> Order`
- `checkout_cart(cart: Cart, user: User | None, customer_name: str, phone: str, address: str, email: str = "") -> Order`
- `update_order_status(order: Order, new_status: str) -> Order`

### 4.4 `AnalyticsService` (`core/services/analytics_service.py`)
- `get_dashboard_metrics() -> dict`

## 5. API Endpoints

### 5.1 Existing Contract Routes (Preserved 100%)
- `GET, POST /api/products`
- `GET, PUT, DELETE /api/products/<id>`
- `GET, POST /api/orders`
- `GET /api/orders/<code_or_id>`
- `PATCH /api/orders/<code_or_id>/status`
- `GET /api/customers`
- `GET, POST /api/articles`
- `GET, PUT, DELETE /api/articles/<id>`
- `GET /api/categories`
- `POST /api/auth/send-code`
- `POST /api/auth/verify-code`
- `GET, PUT /api/me`

### 5.2 New Enhanced Routes
- `GET /api/cart`
- `POST /api/cart/items`
- `PATCH /api/cart/items/<product_id>`
- `DELETE /api/cart/items/<product_id>`
- `POST /api/cart/checkout`
- `GET /api/admin/dashboard/metrics`
- `POST /api/auth/token/refresh`
