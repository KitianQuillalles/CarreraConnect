import os
import sys
from pathlib import Path

# Preparar entorno Django
proj_root = str(Path(__file__).resolve().parents[1])
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CarreraConnect.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from operatividad.models import Area, AsignacionArea

User = get_user_model()

# Definiciones
niveles = [
    (Area.NIVEL_CFT, 'Carrera CFT'),
    (Area.NIVEL_IP, 'Carrera IP'),
    (Area.NIVEL_U, 'Carrera U'),
    (Area.NIVEL_GEN, 'Carrera General'),
]

created = []

for nivel_code, carrera_nombre in niveles:
    # Crear una 'carrera' y un área asociada. Usaremos el mismo objeto Area.
    area_nombre = f"{carrera_nombre} - Área principal"
    area, a_created = Area.objects.get_or_create(nombre=area_nombre, nivel_formacion=nivel_code)
    created.append((area, a_created))

    # Crear Jefe para el área
    jefe_email = f"jefe_{nivel_code.lower()}@example.com"
    if not User.objects.filter(email=jefe_email).exists():
        jefe = User.objects.create_user(username=jefe_email, email=jefe_email, password='password123')
        print('Created user', jefe_email)
    else:
        jefe = User.objects.get(email=jefe_email)
        print('User exists', jefe_email)

    # Asignar rol Jefe
    asign_jefe, _ = AsignacionArea.objects.get_or_create(usuario=jefe, area=area, rol=AsignacionArea.ROL_JEFE)

    # Crear Editor para el área
    editor_email = f"editor_{nivel_code.lower()}@example.com"
    if not User.objects.filter(email=editor_email).exists():
        editor = User.objects.create_user(username=editor_email, email=editor_email, password='password123')
        print('Created user', editor_email)
    else:
        editor = User.objects.get(email=editor_email)
        print('User exists', editor_email)

    asign_ed, _ = AsignacionArea.objects.get_or_create(usuario=editor, area=area, rol=AsignacionArea.ROL_EDITOR)

# Crear un usuario administrador de sistema (rol ADMIN) si no existe
admin_email = 'sistema_admin@example.com'
if not User.objects.filter(email=admin_email).exists():
    admin_user = User.objects.create_user(username=admin_email, email=admin_email, password='adminpass')
    print('Created system admin user', admin_email)
else:
    admin_user = User.objects.get(email=admin_email)
    print('System admin exists', admin_email)

# Asignarle rol ADMIN en la área General (si existe)
try:
    area_gen = Area.objects.filter(nivel_formacion=Area.NIVEL_GEN).first()
    if area_gen:
        AsignacionArea.objects.get_or_create(usuario=admin_user, area=area_gen, rol=AsignacionArea.ROL_ADMIN)
        print('Assigned ADMIN role to', admin_email, 'on area', area_gen)
    else:
        print('No General area found to assign ADMIN role')
except Exception as e:
    print('Error assigning admin role:', e)

print('\nSummary of created/ensured areas and users:')
for area, a_created in created:
    print(f"- Area: {area.nombre} (nivel={area.nivel_formacion})")

print('Finished.')
