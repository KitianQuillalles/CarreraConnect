from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailOrUsernameModelBackend(ModelBackend):
    """Autentica usando correo (email) o el campo username habitual.

    Coloca esta clase en `AUTHENTICATION_BACKENDS` antes del
    `ModelBackend` por defecto para que admin acepte correos.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        user = None
        if username:
            # si contiene '@' intentamos por email (case-insensitive)
            try:
                if '@' in username:
                    user = UserModel.objects.get(email__iexact=username)
                else:
                    user = UserModel.objects.get(**{UserModel.USERNAME_FIELD: username})
            except UserModel.DoesNotExist:
                # fallback: si no existe por nombre, probar por email igualmente
                try:
                    user = UserModel.objects.get(email__iexact=username)
                except UserModel.DoesNotExist:
                    user = None

        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
