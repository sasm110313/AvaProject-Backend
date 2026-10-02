from rest_framework.throttling import AnonRateThrottle as DRFAnonRateThrottle
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.throttling import UserRateThrottle as DRFUserRateThrottle


class AnonRateThrottle(DRFAnonRateThrottle):
    scope = "anon"


class UserRateThrottle(DRFUserRateThrottle):
    scope = "user"


class BurstRateThrottle(SimpleRateThrottle):
    scope = "burst"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class OtpRateThrottle(SimpleRateThrottle):
    scope = "otp"

    def get_cache_key(self, request, view):
        phone = (request.data.get("phone") if hasattr(request, "data") else None) or request.query_params.get("phone")
        if phone:
            return f"throttle_otp_{phone}"
        return self.get_ident(request)


class OtpVerifyRateThrottle(SimpleRateThrottle):
    scope = "otp_verify"

    def get_cache_key(self, request, view):
        phone = (request.data.get("phone") if hasattr(request, "data") else None) or request.query_params.get("phone")
        if phone:
            return f"throttle_otp_verify_{phone}"
        return self.get_ident(request)


class OrderCreateRateThrottle(SimpleRateThrottle):
    scope = "order_create"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return f"throttle_order_{request.user.pk}"
        return self.get_ident(request)
