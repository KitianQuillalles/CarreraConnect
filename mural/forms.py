# mural/forms.py
from django import forms
from django.db.models import Q
from .models import Contenido, Archivo, Area

class ContenidoForm(forms.ModelForm):
    # Definimos colores reales (Hex) para que React los lea correctamente
    COLOR_CHOICES = [
        ('#005c3c', 'Verde Institucional'),
        ("#123a8a", 'Azul Oscuro'),
        ('#17a2b8', 'Celeste Info'),
        ('#ffc107', 'Amarillo'),
        ('#dc3545', 'Rojo Peligro'),
    ]
    color = forms.ChoiceField(
        choices=COLOR_CHOICES, 
        required=False, 
        widget=forms.Select(attrs={"id": "form-color", "class": "select"})
    )
    destinatarios = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"id": "form-destinatarios", "class": "select"}),
        help_text='Seleccione una o más áreas destinatarias (opcional).'
    )

    fecha_publicacion_programada = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={"type": "datetime-local", "id": "form-fecha-publicacion", "class": "input"}),
    )

    fecha_limite = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={"type": "datetime-local", "id": "form-fecha", "class": "input"}),
    )

    niveles_destino = forms.MultipleChoiceField(
        choices=[(Area.NIVEL_U, 'Universidad (U)'), (Area.NIVEL_IP, 'Instituto Profesional (IP)'), (Area.NIVEL_CFT, 'Centro de Formación Técnica (CFT)'), (Area.NIVEL_GEN, 'General (GEN)')],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"id": "form-niveles", "class": "checkboxes"}),
    )

    class Meta:
        model = Contenido
        fields = ["titulo", "contenido", "tipo_contenido", "color"]
        widgets = {
            "titulo": forms.TextInput(attrs={"id": "form-titulo", "class": "input", "placeholder": "Ingrese Título"}),
            # Mapeamos 'contenido' al ID 'form-desc' para que la vista previa JS lo reconozca
            "contenido": forms.Textarea(attrs={"id": "form-desc", "class": "input", "placeholder": "Detalle completo del contenido..."}),
            "tipo_contenido": forms.Select(attrs={"id": "form-tipo", "class": "select"}),
            "color": forms.Select(attrs={"id": "form-color", "class": "select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user

        try:
            if user is None or user.is_superuser:
                areas_qs = Area.objects.all()
            else:
                # CORRECCIÓN CLAVE: Relación correcta con AsignacionArea
                areas_qs = Area.objects.filter(asignaciones__usuario=user).distinct()

            self.fields['destinatarios'].queryset = areas_qs

            if user and not user.is_superuser:
                self.initial['destinatarios'] = list(areas_qs.values_list('id', flat=True))
        except Exception:
            pass

    def clean(self):
        cleaned_data = super().clean()
        destinatarios = cleaned_data.get('destinatarios')
        niveles_destino = cleaned_data.get('niveles_destino')
        tipo_contenido = cleaned_data.get('tipo_contenido')

        # REGLA DE NEGOCIO: Forzar colores según el tipo de contenido
        if tipo_contenido == Contenido.TIPO_CARD:
            cleaned_data['color'] = '#D0F0C0' # Verde claro fijo para tarjetas
        elif tipo_contenido == Contenido.TIPO_ALERTA:
            cleaned_data['color'] = '#1e824c' # Verde oscuro fijo para alertas
        
        if not destinatarios and not niveles_destino:
            raise forms.ValidationError("Debes seleccionar al menos un destinatario (carrera o nivel).")

        user = getattr(self, 'user', None)
        if user and not user.is_superuser:
            allowed = Area.objects.filter(asignaciones__usuario=user).distinct()
            is_dae_like = allowed.filter(nivel_formacion=Area.NIVEL_GEN).exists()
            
            if not is_dae_like:
                if niveles_destino:
                    raise forms.ValidationError("No puede publicar por nivel: su cuenta no pertenece a un Área GEN.")
                bad = [str(a) for a in list(destinatarios or []) if not allowed.filter(pk=a.pk).exists()]
                if bad:
                    raise forms.ValidationError(f"No puede seleccionar áreas fuera de su asignación: {', '.join(bad)}")
        
        return cleaned_data

class ArchivoForm(forms.ModelForm):
    class Meta:
        model = Archivo
        fields = ["ruta_archivo", "tipo_de_archivo"]