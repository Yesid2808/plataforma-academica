from django.conf import settings
from django.db import models
from academico.models import Estudiante


class TipoAlerta(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tipo de alerta'
        verbose_name_plural = 'Tipos de alerta'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ConfiguracionAlerta(models.Model):
    OPERADOR_CHOICES = (
        ('>=', 'Mayor o igual que'),
        ('>', 'Mayor que'),
        ('<=', 'Menor o igual que'),
        ('<', 'Menor que'),
        ('==', 'Igual a'),
    )

    NIVEL_CHOICES = (
        ('ATENCION', 'Atención'),
        ('RIESGO', 'Riesgo'),
        ('CRITICO', 'Crítico'),
    )

    nombre = models.CharField(max_length=150)
    tipo_alerta = models.ForeignKey(
        TipoAlerta,
        on_delete=models.CASCADE,
        related_name='configuraciones'
    )
    operador = models.CharField(max_length=2, choices=OPERADOR_CHOICES, default='>=')
    umbral = models.DecimalField(max_digits=8, decimal_places=2)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES)
    activa = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Configuración de alerta'
        verbose_name_plural = 'Configuraciones de alerta'
        ordering = ['tipo_alerta', 'umbral']

    def __str__(self):
        return f"{self.nombre} - {self.tipo_alerta.nombre}"


class AlertaTemprana(models.Model):
    ESTADO_CHOICES = (
        ('ACTIVA', 'Activa'),
        ('REVISADA', 'Revisada'),
        ('CERRADA', 'Cerrada'),
    )

    NIVEL_CHOICES = (
        ('ATENCION', 'Atención'),
        ('RIESGO', 'Riesgo'),
        ('CRITICO', 'Crítico'),
    )

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='alertas'
    )
    tipo_alerta = models.ForeignKey(
    TipoAlerta,
    on_delete=models.CASCADE,
    related_name='alertas_generadas',
    null=True,
    blank=True

    )
    configuracion = models.ForeignKey(
        ConfiguracionAlerta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_generadas'
    )
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES)
    descripcion = models.TextField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ACTIVA')

    class Meta:
        verbose_name = 'Alerta temprana'
        verbose_name_plural = 'Alertas tempranas'
        ordering = ['-fecha_generacion']
        indexes = [
            models.Index(fields=['estudiante', 'estado'], name='alerta_est_estado_idx'),
            models.Index(fields=['estado', 'nivel', '-fecha_generacion'], name='alerta_estado_nivel_idx'),
            models.Index(fields=['tipo_alerta', '-fecha_generacion'], name='alerta_tipo_fecha_idx'),
        ]

    def __str__(self):
        tipo = self.tipo_alerta.nombre if self.tipo_alerta else 'Sin tipo'
        return f"{self.estudiante} - {tipo} - {self.get_nivel_display()}"


class SeguimientoAlerta(models.Model):
    ACCION_CHOICES = (
        ('CONTACTO_ACUDIENTE', 'Contacto con acudiente'),
        ('APOYO_PEDAGOGICO', 'Apoyo pedagogico'),
        ('REMISION_ORIENTACION', 'Remision a orientacion'),
        ('COMPROMISO_ACADEMICO', 'Compromiso academico'),
        ('OBSERVACION', 'Observacion'),
    )

    RESULTADO_CHOICES = (
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En proceso'),
        ('MEJORA', 'Presenta mejora'),
        ('SIN_MEJORA', 'Sin mejora'),
        ('CERRADO', 'Caso cerrado'),
    )

    alerta = models.ForeignKey(
        AlertaTemprana,
        on_delete=models.CASCADE,
        related_name='seguimientos'
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seguimientos_alertas'
    )
    accion = models.CharField(max_length=30, choices=ACCION_CHOICES)
    descripcion = models.TextField()
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, default='PENDIENTE')
    proxima_revision = models.DateField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Seguimiento de alerta'
        verbose_name_plural = 'Seguimientos de alertas'
        ordering = ['-fecha_registro']
        indexes = [
            models.Index(fields=['alerta', '-fecha_registro'], name='seg_alerta_fecha_idx'),
            models.Index(fields=['resultado', '-fecha_registro'], name='seg_resultado_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.alerta.estudiante} - {self.get_accion_display()} - {self.fecha_registro:%Y-%m-%d}"
