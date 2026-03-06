import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cur.fetchall()]
print('Tables in db.sqlite3:')
for t in tables:
    print(' -', t)
print('\nHas operatividad_contenido:', 'operatividad_contenido' in tables)
print('Has operatividad_asignacionarea:', 'operatividad_asignacionarea' in tables)
conn.close()

def inspect(table):
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info('{table}');")
        cols = cur.fetchall()
        print(f"\nColumns for {table}:")
        for c in cols:
            print('  ', c)
    except Exception as e:
        print(f"Could not inspect {table}: {e}")
    finally:
        conn.close()

inspect('mural_contenido')
inspect('mural_asignacion')
inspect('mural_area')
inspect('mural_archivo')
