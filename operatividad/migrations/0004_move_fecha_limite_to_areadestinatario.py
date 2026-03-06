from django.db import migrations


def forwards_func(apps, schema_editor):
    Contenido = apps.get_model('operatividad', 'Contenido')
    AreaDestinatario = apps.get_model('operatividad', 'AreaDestinatario')
    db_alias = schema_editor.connection.alias
    # Para cada AreaDestinatario sin fecha_limite, copiar la fecha_limite del contenido si existe
    for ad in AreaDestinatario.objects.using(db_alias).select_related('contenido').all():
        try:
            if (not ad.fecha_limite) and getattr(ad.contenido, 'fecha_limite', None):
                ad.fecha_limite = ad.contenido.fecha_limite
                ad.save(update_fields=['fecha_limite'])
        except Exception:
            # ignorar errores individuales
            continue


def reverse_func(apps, schema_editor):
    # En la reversión, no intentamos restaurar estado original: dejar vacío
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('operatividad', '0003_alter_areadestinatario_fecha_asignacion'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
        # luego eliminar el campo fecha_limite de Contenido
        migrations.RemoveField(
            model_name='contenido',
            name='fecha_limite',
        ),
    ]
