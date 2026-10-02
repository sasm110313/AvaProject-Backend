import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("core")


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if isinstance(response.data, dict):
            if "detail" in response.data:
                response.data = {"error": str(response.data["detail"])}
            elif "error" not in response.data:
                first_key = next(iter(response.data.keys()), None)
                first_val = response.data[first_key]
                if isinstance(first_val, list) and first_val:
                    first_msg = f"{first_key}: {first_val[0]}" if first_key != "non_field_errors" else str(first_val[0])
                else:
                    first_msg = f"{first_key}: {first_val}"
                response.data = {"error": first_msg, "errors": response.data}
        elif isinstance(response.data, list) and response.data:
            response.data = {"error": str(response.data[0]), "errors": response.data}
        return response

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            errors = exc.message_dict
            first_msg = next(iter(errors.values()))[0] if errors else "خطای اعتبارسنجی"
            return Response({"error": first_msg, "errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        if hasattr(exc, "messages"):
            return Response({"error": exc.messages[0], "errors": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    logger.exception("Unhandled server exception: %s", exc)
    return Response(
        {"error": "خطای غیرمنتظره در سرور رخ داد. لطفاً مجدداً تلاش نمایید."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
