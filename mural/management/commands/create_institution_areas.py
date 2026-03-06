from django.core.management.base import BaseCommand

from operatividad.models import Area


class Command(BaseCommand):
    help = "Crea áreas/carreras para UST (U), IP y CFT según el listado proporcionado."

    def handle(self, *args, **options):
        created = []
        exists = []

        # Universidad Santo Tomás (UST) - Nivel U
        ust_areas = [
            # Área Salud
            'Enfermería',
            'Kinesiología',
            'Nutrición y Dietética',
            'Tecnología Médica',
            'Terapia Ocupacional',
            'Fonoaudiología',
            # Área Ciencias Sociales y Derecho
            'Derecho',
            'Psicología',
            'Trabajo Social',
            # Área Ingeniería
            'Ingeniería Civil en Minas',
            'Ingeniería Civil Industrial',
            'Ingeniería Civil Informática y Sistemas Inteligentes',
            'Ingeniería Comercial',
            'Geología',
            # Área Educación
            'Pedagogía en Educación Física',
            'Pedagogía en Educación Diferencial',
            'Educación Parvularia',
        ]

        # Instituto Profesional (IP) - Nivel IP
        ip_areas = [
            # Área Ingeniería e Informática
            'Ingeniería en Informática',
            'Ingeniería en Electricidad y Electrónica Industrial',
            'Construcción Civil',
            # Área Administración
            'Ingeniería en Administración de Empresas',
            'Ingeniería en Administración de Recursos Humanos',
            'Contador Auditor',
            # Área Diseño
            'Diseño Gráfico',
            # Área Ciencias Sociales
            'Servicio Social',
        ]

        # Centro de Formación Técnica (CFT) - Nivel CFT
        cft_areas = [
            # Área Salud
            'Técnico en Enfermería',
            'Técnico en Odontología (Mención Higienista Dental)',
            'Técnico en Laboratorio Clínico / Banco de Sangre',
            'Laboratorista Dental',
            # Área Educación
            'Técnico en Educación Especial',
            'Técnico en Educación Parvularia 1° y 2° Básico',
            # Área Administración y Agrícola
            'Técnico en Administración',
            'Técnico Agrícola',
            'Técnico en Veterinaria y Producción Pecuaria',
            # Área Actividad Física y Otros
            'Preparador Físico',
            'Técnico en Deportes',
            'Gastronomía Internacional y Tradicional Chilena',
            'Técnico Jurídico',
        ]

        def create_list(names, nivel):
            for nombre in names:
                area, created_flag = Area.objects.get_or_create(nombre=nombre, defaults={'nivel_formacion': nivel})
                if created_flag:
                    created.append(f"{nombre} ({nivel}) -> id={area.id}")
                else:
                    # ensure nivel is set correctly if found existing without nivel
                    if not area.nivel_formacion:
                        area.nivel_formacion = nivel
                        area.save()
                    exists.append(f"{nombre} ({nivel}) -> id={area.id}")

        create_list(ust_areas, Area.NIVEL_U)
        create_list(ip_areas, Area.NIVEL_IP)
        create_list(cft_areas, Area.NIVEL_CFT)

        self.stdout.write(self.style.SUCCESS('Importación de áreas finalizada.'))
        self.stdout.write(self.style.SUCCESS(f'Creadas: {len(created)}'))
        for c in created:
            self.stdout.write(f'  - {c}')
        self.stdout.write(self.style.WARNING(f'Existentes (no creadas): {len(exists)}'))
        for e in exists:
            self.stdout.write(f'  - {e}')
