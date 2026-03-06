from django.db import migrations


def forwards_func(apps, schema_editor):
    # No data to migrate; field is being removed. Kept as placeholder for forward.
    pass


def reverse_func(apps, schema_editor):
    # On reverse migration, we cannot restore original values. Create field without data.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('operatividad', '0004_move_fecha_limite_to_areadestinatario'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contenido',
            name='fecha_publicado',
        ),
    ]
