from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.companies.models import Company, CompanyMembership


class Command(BaseCommand):
    help = "Компани болон OWNER хэрэглэгчийг үүсгэнэ (нууц үгийг интерактив оруулна)."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("company_slug")
        parser.add_argument("--name", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        if get_user_model().objects.filter(username=options["username"]).exists():
            raise CommandError("Хэрэглэгч байна. Admin хэсгээс membership нэмнэ үү.")
        password = getpass("Нууц үг: ")
        if password != getpass("Нууц үг давтах: "):
            raise CommandError("Нууц үг таарахгүй.")
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from None
        user = get_user_model().objects.create_user(username=options["username"], password=password)
        company, _ = Company.objects.get_or_create(
            slug=options["company_slug"], defaults={"name": options["name"]}
        )
        CompanyMembership.objects.create(company=company, user=user, role="OWNER")
        self.stdout.write(self.style.SUCCESS("OWNER бүртгэл үүслээ."))
