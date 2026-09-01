from django.urls import path

from . import views

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
    path("me", views.profile),
]