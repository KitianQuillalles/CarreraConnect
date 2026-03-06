import sqlite3
import sys

DB = 'db.sqlite3'

rename_map = {
    'mural_area': 'operatividad_area',
    'mural_contenido': 'operatividad_contenido',
    'mural_asignacion': 'operatividad_asignacionarea',
    'mural_archivo': 'operatividad_archivo',
}

steps = []
for old, new in rename_map.items():
    steps.append((f"ALTER TABLE {old} RENAME TO {new};", f"Renamed {old} -> {new}"))

# Column fixes: add user_id copying from usuario_id and add area_origen_id copying from area_id
column_fixes = [
    ("operatividad_asignacionarea", "user_id", "INTEGER", "UPDATE operatividad_asignacionarea SET user_id = usuario_id;", "Added user_id and copied from usuario_id"),
    ("operatividad_contenido", "area_origen_id", "INTEGER", "UPDATE operatividad_contenido SET area_origen_id = area_id;", "Added area_origen_id and copied from area_id"),
]

conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    # Enable foreign keys just in case
    cur.execute('PRAGMA foreign_keys = OFF;')
    conn.commit()
    for sql, msg in steps:
        try:
            print('Running:', sql)
            cur.execute(sql)
            conn.commit()
            print('OK:', msg)
        except Exception as e:
            print('Skipped/failed rename:', sql, '->', e)

    for table, col, coltype, update_sql, msg in column_fixes:
        try:
            # Add column (SQLite allows adding columns)
            add_sql = f"ALTER TABLE {table} ADD COLUMN {col} {coltype};"
            print('Running:', add_sql)
            cur.execute(add_sql)
            conn.commit()
            print('Added column', col, 'to', table)
            # Run update to copy values
            print('Running update:', update_sql)
            cur.execute(update_sql)
            conn.commit()
            print('OK:', msg)
        except Exception as e:
            print('Skipped/failed column fix for', table, col, '->', e)

    print('\nFinal table list:')
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    for t in cur.fetchall():
        print(' -', t[0])

    print('\nDone. Please run: python manage.py migrate')
except Exception as e:
    print('Error during rename script:', e)
    sys.exit(1)
finally:
    cur.execute('PRAGMA foreign_keys = ON;')
    conn.close()
