from django.contrib import admin

from apps.common.admin import ReadOnlyBusinessAdmin

from .models import (
    Comment,
    CommentAutomationRule,
    CommentPrivateReplyAttempt,
    CommentReplyAttempt,
    Post,
    SocialPostCommentAutomation,
)

admin.site.register(Post, ReadOnlyBusinessAdmin)
admin.site.register(Comment, ReadOnlyBusinessAdmin)
admin.site.register(CommentReplyAttempt, ReadOnlyBusinessAdmin)
admin.site.register(CommentAutomationRule, ReadOnlyBusinessAdmin)
admin.site.register(CommentPrivateReplyAttempt, ReadOnlyBusinessAdmin)
admin.site.register(SocialPostCommentAutomation, ReadOnlyBusinessAdmin)
