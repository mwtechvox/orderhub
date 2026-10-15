class PrivateAPIMiddleware:
    """Do not cache authenticated API/OAuth responses or forward callback referrers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store"
            response["Referrer-Policy"] = "no-referrer"
        return response
