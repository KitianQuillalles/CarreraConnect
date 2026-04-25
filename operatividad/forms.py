#operatividad/forms.py
# Formulario para crear/editar usuarios (modelo Usuario)
from django import forms
from django.contrib.auth import get_user_model
from mural.models import Area

User = get_user_model()


class PerfilForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'id': 'perfil_password1'}),
        required=False,
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'id': 'perfil_password2'}),
        required=False,
    )

    class Meta:
        model = User
        # usar campos del modelo User (first_name/last_name)
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={'id': 'perfil_first_name', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'id': 'perfil_last_name', 'autocomplete': 'family-name'}),
        }

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError('Las contraseñas no coinciden')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password1')
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user


class CrearUsuarioForm(forms.Form):
    first_name = forms.CharField(
        label='Nombre', max_length=150,
        widget=forms.TextInput(attrs={'id': 'crear_first_name', 'autocomplete': 'given-name'})
    )
    last_name = forms.CharField(
        label='Apellido', max_length=150, required=False,
        widget=forms.TextInput(attrs={'id': 'crear_last_name', 'autocomplete': 'family-name'})
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'id': 'crear_email', 'autocomplete': 'email'})
    )
    # permitir seleccionar varias áreas al crear un usuario
    area = forms.ModelMultipleChoiceField(
        label='Áreas', queryset=Area.objects.all(), required=False,
        widget=forms.SelectMultiple(attrs={'id': 'crear_area'})
    )
    password1 = forms.CharField(
        label='Contraseña', widget=forms.PasswordInput(attrs={'id': 'crear_password1', 'autocomplete': 'new-password'})
    )
    password2 = forms.CharField(
        label='Confirmar contraseña', widget=forms.PasswordInput(attrs={'id': 'crear_password2', 'autocomplete': 'new-password'})
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') != cleaned.get('password2'):
            raise forms.ValidationError('Las contraseñas no coinciden')
        return cleaned


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
        widgets = {
            'email': forms.EmailInput(attrs={'id': 'usuario_email', 'autocomplete': 'email'}),
            'first_name': forms.TextInput(attrs={'id': 'usuario_first_name', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'id': 'usuario_last_name', 'autocomplete': 'family-name'}),
        }
