from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from operatividad.models import AreaDestinatario


class Command(BaseCommand):
    help = "Marcar como EXPIRADO los AreaDestinatario cuyo fecha_limite ha pasado y estaban PUBLICADOS." 

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List destinatarios that would be changed without modifying them.'
        )
        parser.add_argument(
            '--older-than',
            type=int,
            default=0,
            help='Only process destinatarios expired more than N days ago (default 0).'
        )

    def handle(self, *args, **options):
        now = timezone.now()
        days = options.get('older_than', 0) or 0
        cutoff = now - timedelta(days=days) if days > 0 else now

        qs = AreaDestinatario.objects.filter(fecha_limite__lt=cutoff, estado=AreaDestinatario.ESTADO_PUBLICADO)
        total = qs.count()
        self.stdout.write(f"Found {total} published destinatarios expired before {cutoff.isoformat()}")

        if total == 0:
            return

        if options.get('dry_run'):
            for ad in qs.order_by('fecha_limite'):
                self.stdout.write(f"- id={ad.pk} contenido_id={ad.contenido_id} area_id={ad.area_id} fecha_limite={ad.fecha_limite}")
            return

        updated = qs.update(estado=AreaDestinatario.ESTADO_EXPIRADO)
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} destinatarios to ESTADO_EXPIRADO."))
