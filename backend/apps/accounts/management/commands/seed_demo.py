from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.inbox.services import resolve_conversation, store_message
from apps.meta.models import SocialAccount
from apps.social.models import Comment, Post


class Command(BaseCommand):
    help = "DEMO: токенгүй, DISCONNECTED Page-тай зөвхөн харах өгөгдөл. Бодит Meta integration биш."

    def add_arguments(self, parser):
        parser.add_argument("company_slug")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            company = Company.objects.get(slug=options["company_slug"])
        except Company.DoesNotExist:
            raise CommandError("Эхлээд create_owner командаар компани үүсгэнэ үү.") from None
        account, _ = SocialAccount.objects.get_or_create(
            company=company,
            external_account_id="DEMO-OFFLINE",
            defaults={"display_name": "[DEMO] Дэлгүүр", "status": "DISCONNECTED"},
        )
        post, _ = Post.objects.get_or_create(
            company=company,
            social_account=account,
            external_id="DEMO-POST",
            defaults={
                "message": "[DEMO] Шинэ намрын цуглуулга ирлээ.",
                "reaction_count": 14,
                "comment_count": 1,
                "created_at_platform": timezone.now(),
            },
        )
        Comment.objects.get_or_create(
            company=company,
            social_account=account,
            post=post,
            external_id="DEMO-COMMENT",
            defaults={
                "author_name": "Нараа",
                "message": "Үнэ хэд вэ?",
                "created_at_platform": timezone.now(),
                "can_reply": False,
            },
        )
        conversation = resolve_conversation(account, "DEMO-CUSTOMER", "Бат")
        store_message(
            conversation,
            {
                "id": "DEMO-MESSAGE",
                "message": "[DEMO] M размер байна уу?",
                "from": {"id": "DEMO-CUSTOMER"},
                "created_time": timezone.now().isoformat(),
            },
            notify=True,
        )
        self.stdout.write("DEMO өгөгдөл үүслээ. Facebook рүү хүсэлт илгээгээгүй.")
