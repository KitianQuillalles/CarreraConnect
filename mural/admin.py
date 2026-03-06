from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe
from django.conf import settings
import json
from operatividad.models import Area, Contenido, Archivo, AsignacionArea as Asignacion


class AreaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    list_filter = ()
    search_fields = ("nombre",)


class AsignacionInline(admin.TabularInline):
    model = Asignacion
    extra = 1
    # El nuevo modelo usa campos `usuario` y `rol`.
    fields = ('usuario', 'rol')
    readonly_fields = ()

AreaAdmin.inlines = [AsignacionInline]


class ArchivoInline(admin.TabularInline):
    model = Archivo
    extra = 1
    # Mostrar `tipo_archivo` como solo lectura (eliminamos el input editable)
    fields = ('archivo', 'tipo_archivo', 'tamano')
    readonly_fields = ('tipo_archivo', 'tamano')
    # Usar formset personalizado para validar archivos al subir
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        class ValidatingFormSet(formset):
            def __init__(inner_self, *a, **kw):
                super().__init__(*a, **kw)
                # Para formularios correspondientes a instancias ya existentes,
                # sustituir el widget <input type=file> por un campo de solo lectura
                # que muestre el nombre del archivo y un enlace de descarga.
                for f in getattr(inner_self, 'forms', []):
                    try:
                        if getattr(f.instance, 'pk', None):
                            if 'archivo' in f.fields:
                                # mostrar como texto readonly en vez del file input
                                from django import forms as django_forms
                                name = getattr(f.instance.archivo, 'name', '') or ''
                                display = name.split('/')[-1] if name else ''
                                # crear un widget de texto solo lectura con el nombre
                                f.fields['archivo'].widget = django_forms.TextInput(
                                    attrs={'readonly': 'readonly', 'style': 'width:100%'}
                                )
                                f.initial['archivo'] = display
                                # añadir help_text indicando cómo reemplazar/eliminar
                                f.fields['archivo'].help_text = (
                                    'Archivo existente: para reemplazar elimínelo y luego añada uno nuevo.'
                                )
                    except Exception:
                        pass

            def clean(inner_self):
                super().clean()
                for form in inner_self.forms:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        archivo_field = form.cleaned_data.get('archivo')
                        # Solo validar si se ha subido un nuevo archivo
                        if archivo_field:
                            temp = Archivo(archivo=archivo_field)
                            try:
                                temp.clean()
                            except Exception as e:
                                raise forms.ValidationError(e)

        return ValidatingFormSet

    def get_form(self, request, obj=None, **kwargs):
        """Agregar help_text con enlace de ayuda (signo de interrogación).

        El texto se genera a partir de las constantes en `settings.py`.
        """
        form = super().get_form(request, obj, **kwargs)
        try:
            allowed = getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', [])
            max_mb = getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20)
            size_by_type = getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {})

            allowed_str = ', '.join(f'.{e}' for e in allowed)
            size_by_type_str = ', '.join(f"{k}: {v}MB" for k, v in size_by_type.items())
            msg = (
                f"Extensiones permitidas: {allowed_str}. Tamaño máximo global: {max_mb} MB. "
                f"Límites por tipo: {size_by_type_str}."
            )
            # Insertar un link con clase 'file-help' que el JS detectará
            help_html = mark_safe(f"{msg} &nbsp;<a href='#' class='file-help' data-message='{json.dumps(msg)}'>❔</a>")
            if 'archivo' in form.base_fields:
                form.base_fields['archivo'].help_text = help_html
        except Exception:
            pass
        return form

    class Media:
        js = ('js/admin_file_help.js',)

class ContenidoAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "estado",
        "tipo_contenido",
        "fecha_creacion",
        "autor",
    )
    list_filter = ("estado", "tipo_contenido")
    search_fields = ("titulo", "breve_descripcion", "contenido")
    date_hierarchy = "fecha_creacion"
    # No usar autocomplete para autor en admin para evitar selección rápida por correo
    # Evitar que el campo 'autor' sea editable desde el admin: se asignará automáticamente
    exclude = ('autor',)

    def save_model(self, request, obj, form, change):
        """
        Al crear/editar un Contenido desde el admin:
        - asignar automáticamente el autor al usuario autenticado si es nuevo
        - procesar la lista de archivos subidos (campo `archivos`) y crear
          objetos `Archivo` relacionados.
        """
        is_new = not change or not obj.pk
        if is_new:
            obj.autor = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtrar el campo FK `area` para mostrar solo las áreas asociadas al usuario.

        - Superusers ven todas las áreas.
        - Usuarios normales ven solo `Area.objects.filter(usuario=request.user)`.
        """
        if db_field.name == 'area':
            # importar aquí para evitar importaciones circulares al cargar admin
            from .models import Area as AreaModel
            if request.user.is_superuser:
                kwargs['queryset'] = AreaModel.objects.all()
            else:
                kwargs['queryset'] = AreaModel.objects.filter(usuarios=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    inlines = [ArchivoInline]

class ArchivoAdmin(admin.ModelAdmin):
    list_display = ("archivo", "contenido", "tipo_archivo", "tamano")
    search_fields = ("archivo", "contenido__titulo")
    autocomplete_fields = ("contenido",)
    # Mostrar tipo_archivo como solo lectura en el formulario de edición
    readonly_fields = ('tipo_archivo', 'tamano')

    def get_readonly_fields(self, request, obj=None):
        """Evitar modificar el propio fichero en la vista de cambio; permitir solo eliminación o reemplazo mediante crear nuevo registro."""
        ro = list(self.readonly_fields)
        if obj is not None:
            # hacer que `archivo` sea readonly en la vista de edición
            ro.append('archivo')
        return ro


# Registrar modelos sólo si no están ya registrados por `operatividad.admin`
from django.contrib.admin.sites import AlreadyRegistered

try:
    admin.site.register(Area, AreaAdmin)
except AlreadyRegistered:
    pass

try:
    admin.site.register(Contenido, ContenidoAdmin)
except AlreadyRegistered:
    pass

try:
    admin.site.register(Archivo, ArchivoAdmin)
except AlreadyRegistered:
    pass
