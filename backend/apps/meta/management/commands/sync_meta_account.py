from django.core.management.base import BaseCommand

from apps.meta.tasks import sync_account


class Command(BaseCommand):
    help = "Компани болон account UUID-аар синк хийнэ."

    def add_arguments(self, parser):
        parser.add_argument("company_id")
        parser.add_argument("account_id")

    def handle(self, *args, **options):
        sync_account(options["company_id"], options["account_id"])
