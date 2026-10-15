from django.contrib import admin

from apps.common.admin import ReadOnlyBusinessAdmin

from .models import Conversation, Customer, Message

admin.site.register(Customer, ReadOnlyBusinessAdmin)
admin.site.register(Conversation, ReadOnlyBusinessAdmin)
admin.site.register(Message, ReadOnlyBusinessAdmin)
