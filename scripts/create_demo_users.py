from django.contrib.auth import get_user_model
from mural.models import Area, Asignacion

User = get_user_model()

areas = list(Area.objects.all())
print('AREAS_FOUND:', [(a.id, a.nombre) for a in areas])

samples = [
    ('demo1@local.test','Demo','Uno',[0,1]),
    ('demo2@local.test','Demo','Dos',[1,2]),
    ('demo3@local.test','Demo','Tres',[0,2]),
]

created = []
for email,fn,ln,idxs in samples:
    if any(i>=len(areas) for i in idxs):
        print('Skipping', email, '- not enough areas')
        continue
        try:
            u, created_flag = User.objects.get_or_create(username=email, defaults={'email': email, 'first_name': fn, 'last_name': ln})
        except Exception:
            u, created_flag = User.objects.get_or_create(email=email, defaults={'first_name': fn, 'last_name': ln})
    if created_flag:
        try:
            u.set_password('Password123!')
            u.save()
        except Exception as e:
            print('Error saving password for', email, e)
    for i in idxs:
        a = areas[i]
        Asignacion.objects.get_or_create(area=a, usuario=u)
    created.append((email,[areas[i].nombre for i in idxs]))
    print('Processed', email)

print('SUMMARY:')
from mural.models import Asignacion
all_as = [(str(x.usuario), x.area.nombre, x.es_responsable) for x in Asignacion.objects.select_related('area','usuario').all()]
import pprint
pprint.pprint({'created_users': created, 'all_asignaciones_count': len(all_as), 'all_asignaciones': all_as})
