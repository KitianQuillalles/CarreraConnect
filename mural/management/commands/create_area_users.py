from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from operatividad.models import Area, AsignacionArea


class Command(BaseCommand):
    help = "Crea usuarios de ejemplo: jefe y gestores para áreas Informática y Enfermería."

    def handle(self, *args, **options):
        User = get_user_model()

        created = []

        # Asegurar que las áreas existen
        # Buscar área informática (tomar la primera coincidencia si hay varias)
        area_informatica = Area.objects.filter(nombre__icontains='Informática').first()

        area_enfermeria = Area.objects.filter(nombre__iexact='Enfermería').first()

        # 1) Jefe de área Informática
        if area_informatica:
            u1, c1 = User.objects.get_or_create(username='jefe_informatica', defaults={'email': 'jefe.informatica@example.test', 'first_name': 'Jefe', 'last_name': 'Informática'})
            if c1:
                u1.set_password('password')
                u1.save()
            AsignacionArea.objects.update_or_create(usuario=u1, area=area_informatica, defaults={'rol': AsignacionArea.ROL_JEFE})
            created.append(f'jefe_informatica -> {area_informatica}')

        # 2) Gestor / Analista programación (en Informática)
        if area_informatica:
            u2, c2 = User.objects.get_or_create(username='gestor_informatica', defaults={'email': 'gestor.informatica@example.test', 'first_name': 'Analista', 'last_name': 'Programación'})
            if c2:
                u2.set_password('password')
                u2.save()
            AsignacionArea.objects.update_or_create(usuario=u2, area=area_informatica, defaults={'rol': AsignacionArea.ROL_ADMIN})
            created.append(f'gestor_informatica -> {area_informatica}')

        # 3) Gestor / Jefe de Enfermería
        if area_enfermeria:
            u3, c3 = User.objects.get_or_create(username='gestor_enfermeria', defaults={'email': 'gestor.enfermeria@example.test', 'first_name': 'Gestor', 'last_name': 'Enfermería'})
            if c3:
                u3.set_password('password')
                u3.save()
            AsignacionArea.objects.update_or_create(usuario=u3, area=area_enfermeria, defaults={'rol': AsignacionArea.ROL_ADMIN})
            created.append(f'gestor_enfermeria -> {area_enfermeria}')

        if created:
            self.stdout.write(self.style.SUCCESS('Usuarios/Asignaciones creados:'))
            for c in created:
                self.stdout.write(f' - {c}')
        else:
            self.stdout.write(self.style.WARNING('No se crearon usuarios: no se encontraron las áreas target.'))
