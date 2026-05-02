from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0005_alter_estudiante_genero'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReporteAcudiente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('periodo', models.CharField(choices=[('semanal', 'Semanal'), ('mensual', 'Mensual')], max_length=10)),
                ('fecha_inicio', models.DateField()),
                ('fecha_fin', models.DateField()),
                ('destinatario', models.EmailField(blank=True, max_length=254, null=True)),
                ('estado', models.CharField(choices=[('ENVIADO', 'Enviado'), ('ERROR', 'Error'), ('DESCARGADO', 'Descargado')], max_length=12)),
                ('asunto', models.CharField(blank=True, max_length=200)),
                ('mensaje_error', models.TextField(blank=True, null=True)),
                ('fecha_registro', models.DateTimeField(auto_now_add=True)),
                ('enviado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reportes_enviados', to=settings.AUTH_USER_MODEL)),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reportes_generados', to='academico.estudiante')),
            ],
            options={
                'verbose_name': 'Reporte a acudiente',
                'verbose_name_plural': 'Reportes a acudientes',
                'ordering': ['-fecha_registro'],
            },
        ),
    ]
