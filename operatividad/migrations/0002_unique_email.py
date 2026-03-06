from django.db import migrations


def check_no_duplicate_emails(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    from collections import defaultdict

    buckets = defaultdict(list)
    for u in User.objects.all():
        email = (u.email or '').strip()
        if not email:
            continue
        key = email.lower()
        buckets[key].append(u.pk)

    duplicates = {k: v for k, v in buckets.items() if len(v) > 1}
    if duplicates:
        # Mostrar ejemplo para que el administrador lo corrija manualmente
        raise RuntimeError(
            'No se puede aplicar la migración de unicidad de emails: se encontraron correos duplicados ' 
            f'(case-insensitive). Ejemplos: {dict(list(duplicates.items())[:5])}. ' 
            'Resuelva duplicados antes de ejecutar `python manage.py migrate`.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('operatividad', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(check_no_duplicate_emails),
        migrations.RunSQL(
            # Crear índice único sobre lower(email) (SQLite >= 3.9 / PostgreSQL support)
            sql=(
                "CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_lower_uniq "
                "ON auth_user (lower(email));"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS auth_user_email_lower_uniq;"
            ),
        ),
    ]
