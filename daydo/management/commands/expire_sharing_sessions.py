import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from daydo.models import SharingStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Expire temporary location sharing sessions (LSIP Phase 5).'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_qs = SharingStatus.objects.filter(
            is_sharing_live=True,
            sharing_type='temporary',
            expires_at__lt=now,
        )
        count = expired_qs.update(is_sharing_live=False, updated_at=now)
        if count:
            msg = f"Expired {count} temporary location sharing session(s)."
            logger.info(msg)
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write('No temporary location sharing sessions to expire.')
