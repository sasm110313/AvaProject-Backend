from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from core import views

urlpatterns = [
    path("products", views.product_list),
    path("products/<int:pk>", views.product_detail),
    path("orders", views.order_list),
    path("orders/<str:code>", views.order_detail),
    path("orders/<str:code>/status", views.order_status),
    path("customers", views.customer_list),
    path("articles", views.article_list),
    path("articles/<int:pk>", views.article_detail),
    path("categories", views.category_list),
    path("auth/send-code", views.send_code),
    path("auth/verify-code", views.verify_code),
    path("auth/token/refresh", TokenRefreshView.as_view()),
    path("me", views.profile),
    path("me/orders", views.user_orders),
    path("addresses", views.address_list),
    path("addresses/<int:pk>", views.address_detail),
    path("favorites", views.favorite_view),
    path("favorites/<int:product_id>", views.favorite_view),
    path("cart", views.cart_view),
    path("cart/items", views.cart_add_item),
    path("cart/items/<int:product_id>", views.cart_item_detail),
    path("cart/checkout", views.cart_checkout),
    path("admin/dashboard/metrics", views.dashboard_metrics),
]