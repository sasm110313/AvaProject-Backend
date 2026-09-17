# Backend Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Ava backend into a production-grade modular Django architecture with a unified Custom User/Customer model, JWT/OTP authentication, full Cart subsystem, concurrency-safe Order service, and Admin Analytics, strictly maintaining 100% backward compatibility with the frontend and containing zero explanatory comments.

**Architecture:** Layered service-oriented architecture with thin views, unified `core.User` model (`AUTH_USER_MODEL`), dedicated domain services for Auth, Cart, Order, and Analytics, and atomic transactions with row locks for inventory mutations.

**Tech Stack:** Python 3.12+, Django 6.0.7+, Django REST Framework, djangorestframework-simplejwt, SQLite (dev) / PostgreSQL-ready, Pytest.

**Spec:** `docs/superpowers/specs/2026-09-16-backend-overhaul-design.md`

## Global Constraints
- Zero modifications to any file under `Front/`.
- Absolutely zero explanatory comments in any Python code file.
- Strict type hints on every function signature and return type.
- Row-level locking (`select_for_update`) on all stock decrements.
- 100% API contract compatibility with existing frontend expectations.

---

### Task 1: Environment & Dependencies Setup
- Add `djangorestframework-simplejwt>=5.3.0`, `pytest>=8.0.0`, `pytest-django>=4.8.0` to `requirements.txt`.
- Configure `Ava/settings.py` with `AUTH_USER_MODEL = 'core.User'`, `REST_FRAMEWORK` default authentications (`JWTAuthentication`, `SessionAuthentication`), and SimpleJWT token lifespans.
- Create `pytest.ini` for test suite execution.

### Task 2: Custom User, Customer Unification, and Database Schema
- Create `core/models.py` with `User`, `UserManager`, `Address`, `OtpCode`, `Product`, `ProductImage`, `Cart`, `CartItem`, `Order`, `OrderItem`, `Article`, `ArticleVideo`.
- Ensure `User` model exposes all needed profile fields (`phone`, `name`, `email`, `national_code`, `birth_date`, `gender`, `is_staff`, `is_active`) and properties for backward compatibility.
- Generate and apply Django migrations safely.

### Task 3: Authentication Service & Unified User Endpoints
- Implement `core/services/auth_service.py` with `request_otp` and `verify_otp`.
- Support OTP verification returning JWT tokens (`access`, `refresh`) and customer/user data.
- Update `/api/auth/send-code`, `/api/auth/verify-code`, `/api/auth/token/refresh`, `/api/me`, `/api/customers`.
- Write unit tests for OTP generation, rate limiting, expiry, and token issuance.

### Task 4: Cart Subsystem & Concurrency-Safe Order Service
- Implement `core/services/cart_service.py` for guest (session_key) and authenticated user carts.
- Implement `core/services/order_service.py` featuring atomic transactions and `select_for_update()` on product stock.
- Add endpoints: `GET /api/cart`, `POST /api/cart/items`, `PATCH /api/cart/items/<id>`, `DELETE /api/cart/items/<id>`, `POST /api/cart/checkout`.
- Ensure existing `POST /api/orders` uses `order_service` with concurrency safety.
- Write unit and concurrency integration tests.

### Task 5: Products, Categories, Articles & Admin Contract Verification
- Implement `core/services/product_service.py` and preserve exact multipart form data handling for images and video.
- Preserve `/api/products`, `/api/products/<id>`, `/api/orders`, `/api/orders/<code>/status`, `/api/articles`, `/api/categories`.
- Update `seeddata` management command to populate the new unified models with realistic test data.

### Task 6: Admin Dashboard Analytics
- Implement `core/services/analytics_service.py` calculating revenue, order statuses, low-stock alerts, monthly trends, and bestsellers.
- Expose `GET /api/admin/dashboard/metrics`.

### Task 7: Full Verification & Zero-Comment Audit
- Run the full test suite with Pytest.
- Inspect all modified/created Python files to ensure zero explanatory comments exist.
- Verify migrations, seeding, and contract integrity.
