import os
import sys
from pathlib import Path
import django

# Asegurar que el root del proyecto está en sys.path para importar `CarreraConnect`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CarreraConnect.settings')
django.setup()

from operatividad.models import Contenido

updated = Contenido.objects.update(prioridad=False)
print(f"Registros actualizados: {updated}")
print(f"Total contenidos ahora con prioridad=False: {Contenido.objects.filter(prioridad=False).count()}")
