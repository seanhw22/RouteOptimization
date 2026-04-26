"""Delete guest datasets whose ``expires_at`` is in the past.

Run as a cron job (e.g. daily) to keep the DB tidy. Authenticated-user
datasets are never deleted by this command.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Delete expired guest datasets (and their cascaded experiments / routes).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List datasets that would be deleted without deleting them.',
        )

    def handle(self, *args, **options):
        from datasets.models import Dataset

        now = timezone.now()
        qs = Dataset.objects.filter(user__isnull=True, expires_at__lt=now)
        count = qs.count()

        if options['dry_run']:
            for ds in qs:
                self.stdout.write(f'  would delete: dataset_id={ds.dataset_id} name={ds.name!r} expired_at={ds.expires_at.isoformat()}')
            self.stdout.write(self.style.NOTICE(f'Dry run: {count} dataset(s) would be deleted.'))
            return

        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} expired guest dataset(s) ({deleted} rows total).'))
