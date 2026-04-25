from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User, Permission

from .models import (
    Area,
    AsignacionArea,
    Contenido,
    AreaDestinatario,
    Archivo,
    UsuarioProxy,
)


# Inlines para gestionar la relación many-to-many a través de AsignacionArea
class AsignacionAreaUsuarioInline(admin.TabularInline):
    model = AsignacionArea
    fk_name = 'usuario'
    extra = 1
    verbose_name = 'Asignación de área'
    verbose_name_plural = 'Asignaciones de área'


class AsignacionAreaAreaInline(admin.TabularInline):
    model = AsignacionArea
    fk_name = 'area'
    extra = 1
    verbose_name = 'Usuario asignado'
    verbose_name_plural = 'Usuarios asignados'


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nivel_formacion')
    search_fields = ('nombre',)
    inlines = [AsignacionAreaAreaInline]


@admin.register(AsignacionArea)
class AsignacionAreaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'area', 'rol')
    search_fields = ('usuario__email', 'area__nombre')


@admin.register(Contenido)
class ContenidoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo_contenido', 'fecha_creacion')
    list_filter = ('tipo_contenido',)
    search_fields = ('titulo', 'contenido')


@admin.register(AreaDestinatario)
class AreaDestinatarioAdmin(admin.ModelAdmin):
    list_display = ('contenido', 'area', 'estado', 'fecha_asignacion')
    search_fields = ('contenido__titulo', 'area__nombre')


@admin.register(Archivo)
class ArchivoAdmin(admin.ModelAdmin):
    list_display = ('ruta_archivo', 'contenido', 'tipo_de_archivo')


class UsuarioProxyForm(forms.ModelForm):
    """Formulario simple para el proxy de usuario: no mostrar username."""

    class Meta:
        model = UsuarioProxy
        fields = ('email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')


@admin.register(UsuarioProxy)
class UsuarioProxyAdmin(BaseUserAdmin):
    """Admin para `UsuarioProxy` que evita exponer `username` y muestra email/nombres."""
    form = UsuarioProxyForm
    model = UsuarioProxy
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    inlines = [AsignacionAreaUsuarioInline]

    # Personalizar fieldsets para usar email en lugar de username
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('first_name', 'last_name')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
        ('Fechas importantes', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


# Desregistrar los modelos de auth que no queremos exponer: User y Group
try:
    admin.site.unregister(User)
except Exception:
    pass

try:
    admin.site.unregister(Group)
except Exception:
    pass

try:
    admin.site.unregister(Permission)
except Exception:
    pass

# Mantener el enlace del sitio del admin coherente (opcional)
admin.site.site_header = 'Carrera Connect — Administración'
admin.site.site_title = 'Carrera Connect Admin'
admin.site.index_title = 'Panel de administración'

