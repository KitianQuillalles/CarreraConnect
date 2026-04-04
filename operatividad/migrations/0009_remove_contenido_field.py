from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operatividad', '0008_alter_contenido_prioridad'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contenido',
            name='contenido',
        ),
    ]
