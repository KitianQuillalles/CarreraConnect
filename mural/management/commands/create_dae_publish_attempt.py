from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from operatividad.models import Area, AsignacionArea, Contenido, AreaDestinatario


class Command(BaseCommand):
    help = "Crea datos de ejemplo: usuario DAE, dos áreas en niveles distintos, contenido y un intento de publicación hacia un área diferente"

    def handle(self, *args, **options):
        User = get_user_model()

        # Crear/obtener áreas
        origen, _ = Area.objects.get_or_create(nombre='DAE - Origen', defaults={'nivel_formacion': Area.NIVEL_U})
        destino, _ = Area.objects.get_or_create(nombre='Área Destino (otro nivel)', defaults={'nivel_formacion': Area.NIVEL_CFT})

        # Crear usuario DAE
        username = 'dae_user'
        email = 'dae@example.test'
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password('password')
            user.first_name = 'DAE'
            user.last_name = 'Simulado'
            user.save()

        # Asignar usuario al área de origen con rol Editor
        asignacion, _ = AsignacionArea.objects.get_or_create(usuario=user, area=origen, defaults={'rol': AsignacionArea.ROL_EDITOR})

        # Crear contenido por el usuario en el área origen
        contenido = Contenido.objects.create(
            area_origen=origen,
            titulo='Intento de publicación desde DAE hacia otro nivel',
            breve_descripcion='Prueba: DAE intenta publicar hacia un área de otro nivel',
            contenido='Contenido de prueba generado por create_dae_publish_attempt',
            prioridad=2,
            tipo_contenido=Contenido.TIPO_NOTICIA,
        )

        # Crear AreaDestinatario apuntando a un área con distinto nivel
        ad, created_ad = AreaDestinatario.objects.get_or_create(
            area=destino,
            contenido=contenido,
            defaults={'estado': AreaDestinatario.ESTADO_PUBLICADO, 'fecha_limite': None},
        )

        self.stdout.write(self.style.SUCCESS('Datos creados:'))
        self.stdout.write(f' - Usuario: {user.username} (id={user.id})')
        self.stdout.write(f' - Área origen: {origen} (id={origen.id})')
        self.stdout.write(f' - Área destino: {destino} (id={destino.id})')
        self.stdout.write(f' - Contenido: {contenido.titulo} (id={contenido.id})')
        self.stdout.write(f' - AreaDestinatario: estado={ad.estado} (id={ad.id})')
