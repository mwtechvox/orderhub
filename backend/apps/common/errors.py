from rest_framework.views import exception_handler as drf_handler


def exception_handler(exc, context):
    from rest_framework.response import Response

    from apps.meta.exceptions import MetaError

    if isinstance(exc, MetaError):
        return Response(
            {
                "code": exc.code,
                "message": "Facebook хүсэлт амжилтгүй. Холболт болон зөвшөөрлөө шалгана уу.",
            },
            status=502,
        )
    response = drf_handler(exc, context)
    if response is not None:
        response.data = {
            "code": getattr(exc, "default_code", "INVALID_REQUEST"),
            "message": str(exc.detail)
            if isinstance(getattr(exc, "detail", None), str)
            else "Хүсэлтийг боловсруулах боломжгүй.",
            "details": response.data,
        }
    return response
