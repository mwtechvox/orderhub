from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Company(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    timezone = models.CharField(max_length=64, default="Asia/Ulaanbaatar")

    def __str__(self):
        return self.name


class CompanyMembership(BaseModel):
    class Role(models.TextChoices):
        OWNER = "OWNER"
        ADMIN = "ADMIN"
        AGENT = "AGENT"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role, default=Role.AGENT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "user"], name="membership_unique")
        ]
