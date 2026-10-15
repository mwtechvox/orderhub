from django.contrib import admin

from apps.common.admin import SuperuserAdmin

from .models import Company, CompanyMembership

admin.site.register(Company, SuperuserAdmin)
admin.site.register(CompanyMembership, SuperuserAdmin)
