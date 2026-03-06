import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CarreraConnect.settings')
django.setup()

from django.contrib.auth import get_user_model
from mural.models import Area, Asignacion

User = get_user_model()

email = 'testuser+bot@example.com'
print('Creando/obteniendo usuario', email)
user, created = User.objects.get_or_create(username=email, defaults={'email': email, 'first_name': 'TestBot', 'last_name': 'Usuario'})
if created:
    user.set_password('pass1234')
    user.save()
    print('Usuario creado con id', user.id)
else:
    print('Usuario ya existe con id', user.id)

areas = list(Area.objects.all()[:2])
print('Áreas disponibles para asignar:', [a.nombre for a in areas])
res = []
for a in areas:
    asign, a_created = Asignacion.objects.get_or_create(area=a, usuario=user)
    res.append((a.nombre, a_created))

print('Asignaciones:', res)
print('Usuario -> áreas:', list(user.areas.all().values_list('nombre', flat=True)))
