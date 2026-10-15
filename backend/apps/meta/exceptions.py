from enum import StrEnum


class MetaErrorKind(StrEnum):
    RETRYABLE = "RETRYABLE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    PERMANENT_OTHER = "PERMANENT_OTHER"


class MetaError(Exception):
    code = "META_ERROR"
    kind = MetaErrorKind.PERMANENT_OTHER

    def __init__(self, *, provider_code=None, subcode=None, trace_id=None, retry_after=0):
        super().__init__(self.code)
        self.retry_after = retry_after
        self.safe_payload = {
            "code": self.code,
            "provider_code": provider_code,
            "subcode": subcode,
            "fbtrace_id": trace_id,
        }


class MetaAuthError(MetaError):
    code = "META_AUTH_ERROR"
    kind = MetaErrorKind.AUTH_REQUIRED


class MetaPermissionError(MetaError):
    code = "META_PERMISSION_ERROR"
    kind = MetaErrorKind.PERMISSION_REQUIRED


class MetaRateLimitError(MetaError):
    code = "META_RATE_LIMIT"
    kind = MetaErrorKind.RETRYABLE


class MetaTemporaryError(MetaError):
    code = "META_TEMPORARY_ERROR"
    kind = MetaErrorKind.RETRYABLE


class MetaDeliveryUnknown(MetaError):
    code = "META_DELIVERY_UNKNOWN"
