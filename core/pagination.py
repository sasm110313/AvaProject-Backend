from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ConditionalPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        # Support explicit disable of pagination
        paginate_param = request.query_params.get("paginate", "").lower()
        all_param = request.query_params.get("all", "").lower()
        if paginate_param in ("false", "0", "no") or all_param in ("true", "1", "yes"):
            return None

        # If page or page_size is not requested, return flat list for backward compatibility
        has_page = request.query_params.get(self.page_query_param) is not None
        has_size = request.query_params.get(self.page_size_query_param) is not None
        if not (has_page or has_size):
            return None

        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })
