from django.db import models
from django.conf import settings
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone


"""Modelos de la app `operatividad`.

Cada modelo incluye un breve docstring y metadatos (`class Meta`) en español
para facilitar la lectura y el mantenimiento del código.
"""


class Area(models.Model):
    """Área organizacional (ej.: CFT, IP, U, GEN).

    Contiene nombre, nivel de formación y relaciones con usuarios.
    """
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


class Ubicacion(models.Model):
    """Ubicación física (ej: sede, comuna) según el MER."""
    sede = models.CharField(max_length=100)
    comuna = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Ubicación'
        verbose_name_plural = 'Ubicaciones'

    def __str__(self):
        return f"{self.sede} ({self.comuna})" if self.comuna else self.sede


class Piso(models.Model):
    """Relación entre `Area` y `Ubicacion` con el número/nombre de piso.

    En el MER `Piso` actúa como una entidad asociativa (tiene PK compuesta
    por area+ubicacion). Django no soporta PK compuestas, así que mantenemos
    un id automático pero forzamos la unicidad con `unique_together` para
    replicar la restricción del MER.
    """
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='pisos')
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.CASCADE, related_name='pisos')
    piso = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Piso'
        verbose_name_plural = 'Pisos'
        unique_together = ('area', 'ubicacion')

    def __str__(self):
        return f"{self.piso} - {self.area} @ {self.ubicacion}"


class AsignacionArea(models.Model):
    """Asignación de un usuario a un `Area` con un rol concreto.

    Actúa como tabla intermedia (M2M). Se evita duplicidad con `unique_together`.
    """
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
    """Contenido creado por un área: noticia, evento, logro u otro.

    Incluye prioridad, tipo y fecha de creación. `ordering` muestra primero
    los más prioritarios y recientes.
    """
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
    # El campo `contenido` (texto completo) ha sido eliminado: el detalle
    # ahora se gestiona mediante archivos adjuntos y la `breve_descripcion`.
    # Para compatibilidad en templates/lectura, usar `breve_descripcion`.
    # Cambiado a booleano: marca si el contenido es prioritario o no.
    prioridad = models.BooleanField(default=False)
    tipo_contenido = models.CharField(max_length=10, choices=TIPO_CHOICES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    color = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Contenido'
        verbose_name_plural = 'Contenidos'
        # Ordenar primero por prioridad (True > False), luego por fecha reciente.
        ordering = ['-prioridad', '-fecha_creacion']

    def __str__(self):
        return f"{self.titulo} ({self.area_origen})"


class AreaDestinatario(models.Model):
    """Relación que indica a qué `Area` va dirigido un `Contenido`.

    Guarda estado, fecha de asignación y una posible fecha límite.
    """
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
    """Adjuntos asociados a un `Contenido`.

    Los ficheros se almacenan en la carpeta `mural_adjuntos/` dentro de `MEDIA_ROOT`.
    """

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
    """Eliminar el fichero físico asociado cuando se borra la instancia.

    Se usa el backend de almacenamiento configurado. Los errores se silencian
    para no interrumpir la eliminación del objeto en la base de datos.
    """
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
    """Si se reemplaza el fichero de una instancia existente, borrar el anterior."""
    # Si es creación, no existe fichero anterior
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


"""Proxy/adaptador para exponer los campos legacy del antiguo modelo `Usuario`.

Se reutiliza `auth.User` (no se crea una tabla nueva) y se exponen
propiedades en español para compatibilidad con el código existente.
"""
from django.contrib.auth.models import User as DjangoUser


class UsuarioProxy(DjangoUser):
    """Proxy de `User` que añade accesores en español.

    Útil para conservar llamadas como `usuario.nombre` o
    `usuario.correo_institucional` en el código legado.
    """
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
