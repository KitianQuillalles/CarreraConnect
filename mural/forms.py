from django import forms
from django.db.models import Q
from .models import Contenido, Archivo, Area

NIVELES_CHOICES = [
    ('U', 'Universidad (U)'),
    ('IP', 'Instituto Profesional (IP)'),
    ('CFT', 'Centro de Formación Técnica (CFT)'),
    ('GEN', 'General (GEN)'),
]

class ContenidoForm(forms.ModelForm):
    destinatarios = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"id": "form-destinatarios", "class": "select"}),
        help_text='Seleccione una o más áreas destinatarias (opcional).'
    )

    fecha_publicacion_programada = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={"type": "datetime-local", "id": "form-fecha-publicacion", "class": "input"}),
        help_text='Si se especifica, el contenido quedará en estado "En Espera" hasta esa fecha.'
    )

    fecha_limite = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={"type": "datetime-local", "id": "form-fecha", "class": "input"}),
        help_text='Fecha de expiración aplicable a las áreas seleccionadas (opcional).'
    )

    niveles_destino = forms.MultipleChoiceField(
        choices=[(Area.NIVEL_U, 'Universidad (U)'), (Area.NIVEL_IP, 'Instituto Profesional (IP)'), (Area.NIVEL_CFT, 'Centro de Formación Técnica (CFT)'), (Area.NIVEL_GEN, 'General (GEN)')],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"id": "form-niveles", "class": "checkboxes"}),
        help_text='Seleccione niveles para publicar a todas las carreras de esos niveles (opcional).'
    )

    def __init__(self, *args, **kwargs):
        # Permitimos pasar el usuario actual para filtrar destinos y establecer comportamiento DAE
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # guardar referencia al usuario para validaciones posteriores
        self.user = user

        try:
            if user is None:
                # sin usuario, mostrar todas por defecto
                areas_qs = Area.objects.all()
            elif user.is_superuser:
                areas_qs = Area.objects.all()
            else:
                areas_qs = Area.objects.filter(Q(usuarios=user) | Q(usuario=user)).distinct()

            # Filtrar destinatarios al conjunto pertinente al usuario
            self.fields['destinatarios'].queryset = areas_qs
            # No usamos un selector adicional; `destinatarios` contiene las áreas disponibles según el usuario

            # Si el usuario tiene permisos tipo DAE (aquí: pertenece a nivel GEN o es superuser), aseguramos widget multi-select
            is_dae_like = user.is_superuser if user else False
            if user and not is_dae_like:
                # si el usuario tiene asignaciones en nivel GEN lo consideramos DAE-like
                is_dae_like = areas_qs.filter(nivel_formacion=Area.NIVEL_GEN).exists()

            # mantener widget SelectMultiple (queryset ya limita las opciones para no-DAE)
            self.fields['destinatarios'].widget = forms.SelectMultiple(attrs={"id": "form-destinatarios", "class": "select"})

            # Preselección por defecto: si el usuario no es superuser, seleccionar sus áreas
            if user and not user.is_superuser:
                try:
                    self.initial['destinatarios'] = list(areas_qs.values_list('id', flat=True))
                except Exception:
                    pass
        except Exception:
            # si algo falla, dejar comportamiento por defecto
            pass

    class Meta:
        model = Contenido
        # Ajustado a los nombres de campo en operatividad.models. Se mantiene
        # el id de los widgets para compatibilidad con las plantillas existentes.
        fields = [
            "titulo",
            "breve_descripcion",
            "contenido",
            "tipo_contenido",
            "color",
        ]# NO incluimos 'area_origen' aquí, la asignaremos en la vista automáticamente
        widgets = {
            "breve_descripcion": forms.Textarea(attrs={"rows": 3, "id": "form-desc", "class": "textarea", "maxlength": "150"}),
            "contenido": forms.Textarea(attrs={"rows": 6, "id": "form-contenido", "class": "textarea"}),
            # fecha_limite es ahora un campo del formulario, no un campo del modelo
            "titulo": forms.TextInput(attrs={"id": "form-titulo", "class": "input", "placeholder": "Ingrese Título"}),
            "tipo_contenido": forms.Select(attrs={"id": "form-tipo", "class": "select"}),
            "color": forms.Select(attrs={"id": "form-color", "class": "select"}),
        }
    def clean(self):
        cleaned_data = super().clean()
        destinatarios = cleaned_data.get('destinatarios')
        niveles_destino = cleaned_data.get('niveles_destino')

        # VALIDACIÓN: Debe haber al menos un destino (áreas específicas O un nivel masivo)
        if not destinatarios and not niveles_destino:
            raise forms.ValidationError("Debes seleccionar al menos un destinatario (una carrera o un nivel completo).")

        # Si el usuario NO es DAE-like, asegurar que los destinatarios seleccionados pertenezcan a sus allowed_areas
        user = getattr(self, 'user', None)
        if user and not user.is_superuser:
            # áreas asignadas al usuario
            allowed = Area.objects.filter(Q(usuarios=user) | Q(usuario=user)).distinct()
            # si el usuario no está en GEN, no puede usar niveles_destino
            is_dae_like = allowed.filter(nivel_formacion=Area.NIVEL_GEN).exists()
            if not is_dae_like:
                # validar que niveles_destino no esté usado
                if niveles_destino:
                    raise forms.ValidationError("No puede publicar por nivel: su cuenta no pertenece a un Área GEN.")
                # validar que todos los destinatarios pertenezcan a allowed
                bad = []
                for a in list(destinatarios or []):
                    if not allowed.filter(pk=a.pk).exists():
                        bad.append(str(a))
                if bad:
                    raise forms.ValidationError(f"No puede seleccionar áreas fuera de su asignación: {', '.join(bad)}")
        
        return cleaned_data


class ArchivoForm(forms.ModelForm):
    class Meta:
        model = Archivo
        fields = ["archivo", "tipo_archivo"]
