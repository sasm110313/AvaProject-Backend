from django.urls import re_path
from rest_framework_simplejwt.views import TokenRefreshView

from core import views

urlpatterns = [
    # Products & Catalog
    re_path(r"^products/?$", views.product_list, name="product-list"),
    re_path(r"^products/featured/?$", views.products_featured, name="product-featured"),
    re_path(r"^products/special-offers/?$", views.products_special_offers, name="product-special-offers"),
    re_path(r"^products/best-sellers/?$", views.products_best_sellers, name="product-best-sellers"),
    re_path(r"^products/new-arrivals/?$", views.products_new_arrivals, name="product-new-arrivals"),
    re_path(r"^products/(?P<pk>\d+)/toggle-featured/?$", views.product_toggle_featured, name="product-toggle-featured"),
    re_path(r"^products/batch-action/?$", views.product_batch_action, name="product-batch-action"),
    re_path(r"^products/compare/?$", views.compare_products, name="product-compare"),
    re_path(r"^products/(?P<pk>\d+)/?$", views.product_detail, name="product-detail"),
    re_path(r"^products/(?P<pk>\d+)/variants/?$", views.product_variants, name="product-variants"),
    re_path(r"^variants/(?P<pk>\d+)/?$", views.variant_detail, name="variant-detail"),
    re_path(r"^products/(?P<pk>\d+)/related/?$", views.related_products, name="product-related"),
    re_path(r"^products/(?P<pk>\d+)/reviews/?$", views.product_reviews, name="product-reviews"),
    re_path(r"^products/(?P<pk>\d+)/questions/?$", views.product_questions, name="product-questions"),
    re_path(r"^questions/(?P<question_id>\d+)/answers/?$", views.question_answers, name="question-answers"),
    re_path(r"^brands/?$", views.brand_list, name="brand-list"),

    # Categories
    re_path(r"^categories/?$", views.category_list, name="category-list"),
    re_path(r"^categories/(?P<identifier>[^/]+)/?$", views.category_detail, name="category-detail"),

    # Orders & Checkout & Invoice
    re_path(r"^orders/?$", views.order_list, name="order-list"),
    re_path(r"^orders/(?P<code>[^/]+)/status/?$", views.order_status, name="order-status"),
    re_path(r"^orders/(?P<code>[^/]+)/cancel/?$", views.order_cancel, name="order-cancel"),
    re_path(r"^orders/(?P<code>[^/]+)/history/?$", views.order_history, name="order-history"),
    re_path(r"^orders/(?P<code>[^/]+)/invoice/?$", views.order_invoice, name="order-invoice"),
    re_path(r"^orders/(?P<code>[^/]+)/?$", views.order_detail, name="order-detail"),

    # Customers & Profile
    re_path(r"^customers/?$", views.customer_list, name="customer-list"),
    re_path(r"^customers/(?P<pk>\d+)/?$", views.customer_detail, name="customer-detail"),
    re_path(r"^admin/customers/(?P<pk>\d+)/?$", views.customer_detail, name="admin-customer-detail"),
    re_path(r"^me/?$", views.profile, name="profile"),
    re_path(r"^me/orders/?$", views.user_orders, name="user-orders"),
    re_path(r"^me/avatar/?$", views.upload_avatar, name="user-avatar"),
    re_path(r"^me/messages/?$", views.user_notifications, name="user-messages"),
    re_path(r"^me/messages/(?P<pk>\d+)/read/?$", views.mark_notification_read, name="mark-message-read"),
    re_path(r"^me/messages/read-all/?$", views.mark_all_notifications_read, name="mark-all-messages-read"),

    # Addresses
    re_path(r"^addresses/?$", views.address_list, name="address-list"),
    re_path(r"^addresses/(?P<pk>\d+)/?$", views.address_detail, name="address-detail"),

    # Favorites
    re_path(r"^favorites/?$", views.favorite_view, name="favorites"),
    re_path(r"^favorites/(?P<product_id>\d+)/?$", views.favorite_view, name="favorite-toggle"),

    # Shopping Cart
    re_path(r"^cart/?$", views.cart_view, name="cart"),
    re_path(r"^cart/items/?$", views.cart_add_item, name="cart-add"),
    re_path(r"^cart/items/(?P<product_id>\d+)/?$", views.cart_item_detail, name="cart-item"),
    re_path(r"^cart/coupon/?$", views.cart_apply_coupon, name="cart-coupon"),
    re_path(r"^cart/checkout/?$", views.cart_checkout, name="cart-checkout"),

    # Coupons & Promotions
    re_path(r"^coupons/validate/?$", views.coupon_validate, name="coupon-validate"),

    # Payment Gateway
    re_path(r"^payment/request/?$", views.payment_request, name="payment-request"),
    re_path(r"^payment/verify/?$", views.payment_verify, name="payment-verify"),
    re_path(r"^payment/mock-pay/(?P<authority>[^/]+)/?$", views.mock_payment_page, name="payment-mock"),

    # Homepage & Marketing (Banners & Slideshows)
    re_path(r"^banners/?$", views.banner_list, name="banner-list"),
    re_path(r"^banners/(?P<pk>\d+)/?$", views.banner_detail, name="banner-detail"),
    re_path(r"^banners/reorder/?$", views.banner_reorder, name="banner-reorder"),
    re_path(r"^contact/?$", views.contact_us, name="contact-us"),
    re_path(r"^newsletter/subscribe/?$", views.newsletter_subscribe, name="newsletter-subscribe"),
    re_path(r"^site-settings/?$", views.site_settings_view, name="site-settings"),

    # Blog / Articles
    re_path(r"^articles/?$", views.article_list, name="article-list"),
    re_path(r"^articles/(?P<pk>\d+)/?$", views.article_detail, name="article-detail"),

    # Auth
    re_path(r"^auth/send-code/?$", views.send_code, name="auth-send-code"),
    re_path(r"^auth/verify-code/?$", views.verify_code, name="auth-verify-code"),
    re_path(r"^auth/logout/?$", views.auth_logout, name="auth-logout"),
    re_path(r"^auth/token/refresh/?$", TokenRefreshView.as_view(), name="token-refresh"),

    # Analytics Dashboard & Admin Extensions
    re_path(r"^admin/dashboard/metrics/?$", views.dashboard_metrics, name="dashboard-metrics"),
    re_path(r"^admin/coupons/?$", views.admin_coupon_list, name="admin-coupon-list"),
    re_path(r"^admin/coupons/(?P<pk>\d+)/?$", views.admin_coupon_detail, name="admin-coupon-detail"),
    re_path(r"^admin/reviews/?$", views.admin_review_list, name="admin-review-list"),
    re_path(r"^admin/reviews/(?P<pk>\d+)/?$", views.admin_review_detail, name="admin-review-detail"),
    re_path(r"^admin/contact-messages/?$", views.admin_contact_list, name="admin-contact-list"),
    re_path(r"^admin/contact-messages/(?P<pk>\d+)/?$", views.admin_contact_detail, name="admin-contact-detail"),
]
