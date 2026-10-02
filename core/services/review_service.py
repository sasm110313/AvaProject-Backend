from typing import Any
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count

from core.models import Product, ProductReview, User


class ReviewService:
    @classmethod
    def get_product_reviews(cls, product_id: int) -> dict[str, Any]:
        reviews_qs = ProductReview.objects.filter(product_id=product_id, is_approved=True)

        stats = reviews_qs.aggregate(avg_rating=Avg("rating"), total_count=Count("id"))
        avg_rating = round(stats["avg_rating"] or 5.0, 1)
        total_count = stats["total_count"]

        # Rating distribution (1 to 5 stars)
        distribution = {star: 0 for star in range(1, 6)}
        for item in reviews_qs.values("rating").annotate(count=Count("id")):
            distribution[item["rating"]] = item["count"]

        return {
            "average_rating": avg_rating,
            "total_reviews": total_count,
            "distribution": distribution,
            "reviews": reviews_qs,
        }

    @classmethod
    @transaction.atomic
    def add_review(
        cls,
        product_id: int,
        rating: int,
        comment: str,
        user: User | None = None,
        user_name: str = "",
        pros: list[str] | None = None,
        cons: list[str] | None = None,
    ) -> ProductReview:
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise ValidationError("محصول مورد نظر یافت نشد")

        if rating < 1 or rating > 5:
            raise ValidationError("امتیاز باید بین ۱ تا ۵ باشد")

        comment = comment.strip()
        if not comment:
            raise ValidationError("متن نظر نمی‌تواند خالی باشد")

        if user and user.is_authenticated:
            display_name = user.name or user.phone
        else:
            display_name = user_name.strip() or "کاربر ناشناس"

        review = ProductReview.objects.create(
            product=product,
            user=user if (user and user.is_authenticated) else None,
            user_name=display_name,
            rating=rating,
            comment=comment,
            pros=pros or [],
            cons=cons or [],
            is_approved=True,
        )

        # Recalculate average rating for product
        avg = ProductReview.objects.filter(product=product, is_approved=True).aggregate(Avg("rating"))["rating__avg"]
        if avg:
            product.rating = round(avg, 1)
            product.save(update_fields=["rating"])

        return review
