from typing import Any
from django.core.exceptions import ValidationError
from django.db.models import Count, QuerySet
from django.utils.text import slugify

from core.models import Category


class CategoryService:
    @classmethod
    def list_categories(
        cls,
        parent_only: bool = False,
        active_only: bool = True,
    ) -> QuerySet[Category]:
        qs = Category.objects.annotate(products_count=Count("products"))
        if active_only:
            qs = qs.filter(is_active=True)
        if parent_only:
            qs = qs.filter(parent__isnull=True)
        return qs.select_related("parent").prefetch_related("children")

    @classmethod
    def get_category(cls, identifier: str | int) -> Category:
        qs = Category.objects.annotate(products_count=Count("products")).prefetch_related("children")
        if str(identifier).isdigit():
            category = qs.filter(id=int(identifier)).first()
        else:
            category = qs.filter(slug=identifier).first()

        if not category:
            raise ValidationError("دسته‌بندی مورد نظر یافت نشد")
        return category

    @classmethod
    def create_category(cls, data: dict[str, Any]) -> Category:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValidationError("نام دسته‌بندی الزامی است")

        slug = (data.get("slug") or "").strip()
        if not slug:
            slug = slugify(name, allow_unicode=True) or f"cat-{name}"

        parent_id = data.get("parent_id")
        parent = None
        if parent_id:
            parent = Category.objects.filter(id=parent_id).first()

        return Category.objects.create(
            name=name,
            slug=slug,
            parent=parent,
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            display_order=int(data.get("display_order", 0)),
            is_active=data.get("is_active", True),
        )
