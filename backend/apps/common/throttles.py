from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class LoginThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class WriteThrottle(UserRateThrottle):
    scope = "write"


class CompanyThrottle(SimpleRateThrottle):
    scope = "company"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": request.active_company.pk}
