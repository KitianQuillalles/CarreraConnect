from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.conf import settings
import os
import shutil

from operatividad.models import Contenido
from django.db.models import Max


class Command(BaseCommand):
    help = "Delete or archive Contenido objects whose fecha_limite is in the past and handle attached files." 

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List expired contenidos and attached files without performing actions.'
        )
        parser.add_argument(
            '--older-than',
            type=int,
            default=0,
            help='Only act on contenidos expired more than N days ago (default 0).'
        )
        parser.add_argument(
            '--archive',
            action='store_true',
            help='Archive contenidos instead of deleting. Files will be moved to an "archivado" subfolder and estado set to BORRADOR.'
        )
        parser.add_argument(
            '--archive-dir',
            type=str,
            default='archivado',
            help='Subdirectory under the app upload folder where archived files will be moved (default: archivado).'
        )

    def handle(self, *args, **options):
        now = timezone.now()
        days = options.get('older_than', 0) or 0
        cutoff = now - timedelta(days=days) if days > 0 else now

        # Seleccionar contenidos cuyos destinatarios tienen fecha_limite menor que el cutoff
        qs = Contenido.objects.annotate(max_fecha_limite=Max('destinatarios__fecha_limite')).filter(max_fecha_limite__lt=cutoff)
        total = qs.count()
        mode = 'ARCHIVE' if options.get('archive') else 'DELETE'
        self.stdout.write(f"Mode: {mode}. Found {total} expired contenidos (fecha_limite < {cutoff.isoformat()})")

        if total == 0:
            return

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        upload_base = 'mural_archivos'
        archive_dir = options.get('archive_dir') or 'archivado'

        for contenido in qs.order_by('max_fecha_limite'):
            title = getattr(contenido, 'titulo', str(contenido))
            self.stdout.write(f"- id={contenido.pk} titulo={title!r} max_fecha_limite={getattr(contenido, 'max_fecha_limite', None)}")

            archivos = list(contenido.archivos.all())
            if archivos:
                for a in archivos:
                    nombre = getattr(a.archivo, 'name', None)
                    self.stdout.write(f"    archivo: {nombre}")
            else:
                self.stdout.write("    (sin archivos adjuntos)")

            if options.get('dry_run'):
                continue

            if options.get('archive'):
                # Archivar: mover archivos a subcarpeta y marcar contenido como BORRADOR (no borrar registros)
                with transaction.atomic():
                    for a in archivos:
                        try:
                            # intentar mover fichero en disco si MEDIA_ROOT disponible
                            if media_root and hasattr(a.archivo, 'path'):
                                src = a.archivo.path
                                if src and os.path.exists(src):
                                    target_dir = os.path.join(media_root, upload_base, archive_dir)
                                    os.makedirs(target_dir, exist_ok=True)
                                    dest = os.path.join(target_dir, os.path.basename(src))
                                    # evitar sobrescribir: si existe, añadir sufijo
                                    if os.path.exists(dest):
                                        base, ext = os.path.splitext(os.path.basename(src))
                                        i = 1
                                        while True:
                                            candidate = f"{base}_{i}{ext}"
                                            dest = os.path.join(target_dir, candidate)
                                            if not os.path.exists(dest):
                                                break
                                            i += 1
                                    shutil.move(src, dest)
                                    # actualizar campo FileField para apuntar al nuevo nombre relativo
                                    rel_path = os.path.relpath(dest, media_root).replace('\\', '/')
                                    a.archivo.name = rel_path
                                    a.save(update_fields=['archivo'])
                                else:
                                    self.stderr.write(f"Warning: archivo físico no encontrado: {src}")
                            else:
                                self.stderr.write("Warning: MEDIA_ROOT no disponible o archivo.path no accesible; no se mueve el archivo.")
                        except Exception as e:
                            self.stderr.write(f"Error moviendo archivo id={a.pk}: {e}")

                    # marcar contenido como archivado (prefijo en título). No existe campo 'estado' en el modelo centralizado.
                    try:
                        if not str(contenido.titulo).startswith('[ARCHIVADO]'):
                            contenido.titulo = f"[ARCHIVADO] {contenido.titulo}"
                            contenido.save(update_fields=['titulo'])
                    except Exception as e:
                        self.stderr.write(f"Error marcando contenido id={contenido.pk} como archivado: {e}")

            else:
                # Eliminación: borrar archivos físicos y registros
                with transaction.atomic():
                    for a in archivos:
                        try:
                            a.archivo.delete(save=False)
                        except Exception:
                            try:
                                path = a.archivo.path
                                if path and os.path.exists(path):
                                    os.remove(path)
                            except Exception:
                                pass
                        try:
                            a.delete()
                        except Exception:
                            pass
                    try:
                        contenido.delete()
                    except Exception as e:
                        self.stderr.write(f"Error al eliminar Contenido id={contenido.pk}: {e}")

        self.stdout.write(self.style.SUCCESS('Operación completada.'))
