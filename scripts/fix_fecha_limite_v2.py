"""
Versión más robusta del script para corregir `mural_contenido.fecha_limite`.
- Hace backup de `db.sqlite3`.
- Muestra tipos SQLite (`typeof`) de las filas con fecha_limite no NULL.
- Convierte valores que no son `text` a texto usando `CAST(... AS TEXT)`.
- Añade ' 23:59:00' a valores textuales con formato `YYYY-MM-DD` (longitud 10).

Uso:
  python scripts\fix_fecha_limite_v2.py

Siempre revisa el backup si algo sale mal.
"""
import sqlite3
import shutil
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent.parent
DB = BASE / 'db.sqlite3'
BACKUP = BASE / 'db.sqlite3.fix_fecha_lim_v2.bak'

if not DB.exists():
    print(f"ERROR: no se encontró la base de datos en {DB}")
    raise SystemExit(1)

print(f"Creando backup: {BACKUP}")
shutil.copy2(DB, BACKUP)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

print("Tipos actuales de fecha_limite (muestra hasta 50 filas):")
for row in cur.execute("SELECT id, typeof(fecha_limite), fecha_limite FROM mural_contenido WHERE fecha_limite IS NOT NULL LIMIT 50"):
    print(row)

# Convertir filas donde typeof != 'text' a texto
print('\nConvirtiendo valores no-text a texto (si existen)...')
cur.execute("SELECT COUNT(*) FROM mural_contenido WHERE fecha_limite IS NOT NULL AND typeof(fecha_limite) != 'text'")
non_text_count = cur.fetchone()[0]
print('Filas con tipo != text:', non_text_count)
if non_text_count:
    cur.execute("UPDATE mural_contenido SET fecha_limite = CAST(fecha_limite AS TEXT) WHERE fecha_limite IS NOT NULL AND typeof(fecha_limite) != 'text'")
    conn.commit()
    print('Conversión a texto completada.')

# Ahora añadir hora a las fechas con longitud 10 y que parezcan YYYY-MM-DD
pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
cur.execute("SELECT id, fecha_limite FROM mural_contenido WHERE fecha_limite IS NOT NULL AND LENGTH(fecha_limite)=10")
rows = cur.fetchall()
print('\nFilas con longitud 10 a revisar:', len(rows))
updated = 0
for pk, val in rows:
    if isinstance(val, bytes):
        try:
            val = val.decode('utf-8')
        except Exception:
            continue
    if not isinstance(val, str):
        continue
    if pattern.match(val):
        newval = val + ' 23:59:00'
        cur.execute("UPDATE mural_contenido SET fecha_limite = ? WHERE id = ?", (newval, pk))
        updated += 1

conn.commit()
print('Filas actualizadas con hora añadida:', updated)

print('\nTipos de fecha_limite después de cambios (muestra hasta 50 filas):')
for row in cur.execute("SELECT id, typeof(fecha_limite), fecha_limite FROM mural_contenido WHERE fecha_limite IS NOT NULL LIMIT 50"):
    print(row)

cur.close()
conn.close()
print('\nListo. Si necesitas revertir: copia el backup sobre db.sqlite3.')