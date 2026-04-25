from django.db import models
from django.conf import settings
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User as DjangoUser

class Area(models.Model):
    NIVEL_CFT = 'CFT'
    NIVEL_IP = 'IP'
    NIVEL_U = 'U'
    NIVEL_GEN = 'GEN'

    NIVEL_CHOICES = [
        (NIVEL_CFT, 'CFT'),
        (NIVEL_IP, 'IP'),
        (NIVEL_U, 'U'),
        (NIVEL_GEN, 'GEN'),
    ]

    nombre = models.CharField(max_length=100)
    nivel_formacion = models.CharField(max_length=3, choices=NIVEL_CHOICES)
    class Meta:
        verbose_name = 'Área'
        verbose_name_plural = 'Áreas'

    def __str__(self):
        return f"{self.nombre} ({self.nivel_formacion})"


class AsignacionArea(models.Model):
    ROL_JEFE = 'Jefe de área'
    ROL_ADMIN = 'Administrador'
    ROL_EDITOR = 'Editor de contenido'

    ROL_CHOICES = [
        (ROL_JEFE, 'Jefe de área'),
        (ROL_ADMIN, 'Administrador'),
        (ROL_EDITOR, 'Editor de contenido'),
    ]

    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='asignaciones')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='asignaciones_area')
    rol = models.CharField(max_length=30, choices=ROL_CHOICES)
    ubicacion = models.CharField(max_length=100, blank=True) # Adaptado del MER

    class Meta:
        verbose_name = 'Asignación de Área'
        verbose_name_plural = 'Asignaciones de Área'
        unique_together = ('area', 'usuario')

    def __str__(self):
        return f"{self.usuario} -> {self.area} ({self.rol})"


class Contenido(models.Model):
    # Usaremos Tipo_Contenido para definir el comportamiento visual (MVP)
    TIPO_CARD = 'CARD'
    TIPO_BANNER = 'BANNER'
    TIPO_ALERTA = 'ALERTA'

    TIPO_CHOICES = [
        (TIPO_CARD, 'Tarjeta (Mural)'),
        (TIPO_BANNER, 'Banner Principal'),
        (TIPO_ALERTA, 'Alerta (15s)'),
    ]

    titulo = models.CharField(max_length=200)
    contenido = models.TextField() # Reemplaza a breve_descripcion / cuerpo
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    color = models.CharField(max_length=20, blank=True)
    tipo_contenido = models.CharField(max_length=10, choices=TIPO_CHOICES, default=TIPO_CARD)

    class Meta:
        verbose_name = 'Contenido'
        verbose_name_plural = 'Contenidos'

    def __str__(self):
        return f"[{self.get_tipo_contenido_display()}] {self.titulo}"


class AreaDestinatario(models.Model):
    ESTADO_BORRADOR = 'BORRADOR'
    ESTADO_PUBLICADO = 'PUBLICADO'
    ESTADO_EN_ESPERA = 'EN_ESPERA'
    ESTADO_EXPIRADO = 'EXPIRADO'

    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, 'Borrador'),
        (ESTADO_PUBLICADO, 'Publicado'),
        (ESTADO_EN_ESPERA, 'En Espera'),
        (ESTADO_EXPIRADO, 'Expirado'),
    ]

    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='destinatarios')
    contenido = models.ForeignKey(Contenido, on_delete=models.CASCADE, related_name='destinatarios')
    fecha_asignacion = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    fecha_limite = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Área Destinatario'
        verbose_name_plural = 'Áreas Destinatarias'
        unique_together = ('area', 'contenido')

    def __str__(self):
        return f"{self.contenido} -> {self.area} [{self.estado}]"


class Archivo(models.Model):
    contenido = models.ForeignKey(Contenido, on_delete=models.CASCADE, related_name='archivos')
    ruta_archivo = models.FileField(upload_to='mural_adjuntos/') # Renombrado según MER
    tipo_de_archivo = models.CharField(max_length=50, blank=True) # Renombrado según MER

    class Meta:
        verbose_name = 'Archivo'
        verbose_name_plural = 'Archivos'

    def __str__(self):
        return self.ruta_archivo.name

# --- SIGNALS Y PROXY (Sin cambios, son lógica interna de Django, no rompen el MER) ---
@receiver(post_delete, sender=Archivo)
def archivo_post_delete(sender, instance, **kwargs):
    try:
        if instance.ruta_archivo:
            storage = instance.ruta_archivo.storage
            name = instance.ruta_archivo.name
            if name and storage.exists(name):
                storage.delete(name)
    except Exception:
        pass

@receiver(pre_save, sender=Archivo)
def archivo_pre_save_delete_old(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Archivo.objects.get(pk=instance.pk)
    except Archivo.DoesNotExist:
        return
    try:
        old_name = old.ruta_archivo.name
        new_name = instance.ruta_archivo.name
        if old_name and old_name != new_name:
            storage = old.ruta_archivo.storage
            if storage.exists(old_name):
                storage.delete(old_name)
    except Exception:
        pass

class UsuarioProxy(DjangoUser):
    class Meta:
        proxy = True
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'