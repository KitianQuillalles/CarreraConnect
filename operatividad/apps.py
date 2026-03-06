from django.apps import AppConfig


class OperatividadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'operatividad'
    verbose_name = 'Autenticación y Autorización'
    def ready(self):
        # Importar señales para que queden registradas al arrancar Django
        try:
            import operatividad.signals  # noqa: F401
        except Exception:
            # Evitar que errores al importar señales rompan el arranque del proyecto
            pass
