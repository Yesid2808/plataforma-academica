from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_notificacionusuario'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditoriaCambio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('ASISTENCIA', 'Asistencia'), ('CALIFICACION', 'Calificacion'), ('SISTEMA', 'Sistema')], default='SISTEMA', max_length=20)),
                ('accion', models.CharField(choices=[('CREACION', 'Creacion'), ('EDICION', 'Edicion'), ('ELIMINACION', 'Eliminacion')], default='EDICION', max_length=20)),
                ('modulo', models.CharField(max_length=50)),
                ('titulo', models.CharField(max_length=180)),
                ('descripcion', models.TextField()),
                ('estudiante_codigo', models.CharField(blank=True, max_length=20)),
                ('estudiante_nombre', models.CharField(blank=True, max_length=200)),
                ('grupo', models.CharField(blank=True, max_length=50)),
                ('asignatura', models.CharField(blank=True, max_length=120)),
                ('fecha_referencia', models.DateField(blank=True, null=True)),
                ('valor_anterior', models.CharField(blank=True, max_length=255)),
                ('valor_nuevo', models.CharField(blank=True, max_length=255)),
                ('referencia_url', models.CharField(blank=True, max_length=255, null=True)),
                ('datos_extra', models.JSONField(blank=True, default=dict)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='auditorias_realizadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Auditoria de cambio',
                'verbose_name_plural': 'Auditorias de cambios',
                'ordering': ['-fecha_creacion'],
            },
        ),
    ]
