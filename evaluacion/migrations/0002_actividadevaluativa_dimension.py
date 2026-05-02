from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluacion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='actividadevaluativa',
            name='dimension',
            field=models.CharField(
                choices=[
                    ('PARCIAL', 'Parcial (40%)'),
                    ('ACTIVIDADES', 'Actividades (40%)'),
                    ('ACTITUDINAL', 'Actitudinal (20%)'),
                ],
                default='ACTIVIDADES',
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name='actividadevaluativa',
            index=models.Index(fields=['carga_academica', 'periodo', 'dimension'], name='act_carga_periodo_dim_idx'),
        ),
    ]
