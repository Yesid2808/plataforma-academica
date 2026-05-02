from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0006_reporteacudiente'),
    ]

    operations = [
        migrations.CreateModel(
            name='HorarioClase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dia_semana', models.PositiveSmallIntegerField(choices=[(1, 'Lunes'), (2, 'Martes'), (3, 'Miercoles'), (4, 'Jueves'), (5, 'Viernes')])),
                ('hora_inicio', models.TimeField()),
                ('hora_fin', models.TimeField()),
                ('aula', models.CharField(blank=True, max_length=50, null=True)),
                ('carga_academica', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='horarios', to='academico.cargaacademica')),
            ],
            options={
                'verbose_name': 'Horario de clase',
                'verbose_name_plural': 'Horarios de clase',
                'ordering': ['dia_semana', 'hora_inicio', 'carga_academica__grupo__grado__nombre', 'carga_academica__grupo__nombre'],
            },
        ),
    ]
