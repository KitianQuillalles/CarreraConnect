from django.db import models
from django.conf import settings
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone


# Todos los modelos solicitados viven en esta app `operatividad`.
# Para soportar tanto el User por defecto como un modelo de usuario personalizado
# la relación con usuario usa la referencia configurada en settings.AUTH_USER_MODEL.


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
    # Compatibilidad con código existente: relación M2M hacia usuarios
    # usando la tabla intermedia `AsignacionArea`.
    usuarios = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='AsignacionArea',
        related_name='areas'
    )
    # Usuario responsable (compatibilidad con `mural` y código antiguo).
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='areas_responsables',
        null=True,
        blank=True,
    )

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

    # Campo renombrado a `usuario` para mantener compatibilidad con el código
    # existente que usaba ese nombre. Se añade un alias `user` para comodidad.
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='asignaciones_area')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='asignaciones')
    rol = models.CharField(max_length=30, choices=ROL_CHOICES)

    class Meta:
        verbose_name = 'Asignación de Área'
        verbose_name_plural = 'Asignaciones de Área'
        unique_together = ('usuario', 'area')

    def __str__(self):
        return f"{self.usuario} -> {self.area} ({self.rol})"

    # Alias para código que todavía accede a `user`.
    @property
    def user(self):
        return self.usuario

    @user.setter
    def user(self, value):
        self.usuario = value


class Contenido(models.Model):
    TIPO_NOTICIA = 'NOTICIA'
    TIPO_EVENTO = 'EVENTO'
    TIPO_LOGRO = 'LOGRO'
    TIPO_OTRO = 'OTRO'

    TIPO_CHOICES = [
        (TIPO_NOTICIA, 'Noticia'),
        (TIPO_EVENTO, 'Evento'),
        (TIPO_LOGRO, 'Logro'),
        (TIPO_OTRO, 'Otro'),
    ]
    area_origen = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='contenidos_origen')
    titulo = models.CharField(max_length=200)
    breve_descripcion = models.CharField(max_length=255)
    contenido = models.TextField()
    prioridad = models.PositiveSmallIntegerField(default=3)
    tipo_contenido = models.CharField(max_length=10, choices=TIPO_CHOICES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    color = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Contenido'
        verbose_name_plural = 'Contenidos'
        ordering = ['-prioridad', '-fecha_creacion']

    def __str__(self):
        return f"{self.titulo} ({self.area_origen})"


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
    fecha_limite = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES)

    class Meta:
        verbose_name = 'Área Destinatario'
        verbose_name_plural = 'Áreas Destinatarias'
        unique_together = ('area', 'contenido')

    def __str__(self):
        return f"{self.contenido} -> {self.area} [{self.estado}]"


class Archivo(models.Model):
    contenido = models.ForeignKey(Contenido, on_delete=models.CASCADE, related_name='archivos')
    archivo = models.FileField(upload_to='mural_adjuntos/')
    tipo_archivo = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = 'Archivo'
        verbose_name_plural = 'Archivos'

    def __str__(self):
        return f"{self.archivo.name} ({self.contenido.titulo})"


@receiver(post_delete, sender=Archivo)
def archivo_post_delete(sender, instance, **kwargs):
    try:
        if instance.archivo:
            storage = instance.archivo.storage
            name = instance.archivo.name
            if name and storage.exists(name):
                storage.delete(name)
    except Exception:
        pass


@receiver(pre_save, sender=Archivo)
def archivo_pre_save_delete_old(sender, instance, **kwargs):
    # si estamos reemplazando un archivo existente, eliminar el fichero anterior
    if not instance.pk:
        return
    try:
        old = Archivo.objects.get(pk=instance.pk)
    except Archivo.DoesNotExist:
        return
    try:
        old_name = old.archivo.name
        new_name = instance.archivo.name
        if old_name and old_name != new_name:
            storage = old.archivo.storage
            if storage.exists(old_name):
                storage.delete(old_name)
    except Exception:
        pass


# Proxy/adaptador para exponer los campos legacy del antiguo modelo `Usuario`
# como propiedades sobre el `auth.User` usado en settings.AUTH_USER_MODEL.
from django.contrib.auth.models import User as DjangoUser


class UsuarioProxy(DjangoUser):
    class Meta:
        proxy = True
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    # nombres en español (compatibilidad con código existente)
    @property
    def nombre(self):
        return self.first_name

    @nombre.setter
    def nombre(self, value):
        self.first_name = value

    @property
    def apellidos(self):
        return self.last_name

    @apellidos.setter
    def apellidos(self, value):
        self.last_name = value

    @property
    def correo_institucional(self):
        return self.email

    @correo_institucional.setter
    def correo_institucional(self, value):
        self.email = value

    def get_full_name_spanish(self):
        return f"{self.nombre} {self.apellidos}".strip()
