from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import CSRFView, LoginView, LogoutView, MeView
from apps.companies.views import CompanyViewSet
from apps.inbox.views import ConversationViewSet, SendMessageView
from apps.meta.views import AccountViewSet, CallbackView, ConnectView, PagesView
from apps.meta.webhook_views import webhook
from apps.social.views import CommentReplyView, PostViewSet

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("posts", PostViewSet, basename="post")
router.register("meta/accounts", AccountViewSet, basename="meta-account")
router.register("companies", CompanyViewSet, basename="company")

urlpatterns = [
    path("api/meta/webhook/", webhook),
    # Meta may normalize the callback URL and omit the trailing slash on POST.
    # Accept both forms so Django does not redirect a POST and lose its body.
    path("api/meta/webhook", webhook),
    path("api/messages/send/", SendMessageView.as_view()),
    path("api/comments/<uuid:pk>/reply/", CommentReplyView.as_view()),
    path("api/meta/facebook/connect/", ConnectView.as_view()),
    path("api/meta/facebook/callback/", CallbackView.as_view()),
    path("api/meta/facebook/pages/", PagesView.as_view()),
    path("health/", lambda request: JsonResponse({"ok": True})),
    path("admin/", admin.site.urls),
    path("api/auth/csrf/", CSRFView.as_view()),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/auth/me/", MeView.as_view()),
    path("api/", include(router.urls)),
]
