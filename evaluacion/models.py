from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from academico.models import CargaAcademica, Estudiante, PeriodoAcademico


class ActividadEvaluativa(models.Model):
    DIMENSION_PARCIAL = 'PARCIAL'
    DIMENSION_ACTIVIDADES = 'ACTIVIDADES'
    DIMENSION_ACTITUDINAL = 'ACTITUDINAL'
    DIMENSION_CHOICES = (
        (DIMENSION_PARCIAL, 'Parcial (40%)'),
        (DIMENSION_ACTIVIDADES, 'Actividades (40%)'),
        (DIMENSION_ACTITUDINAL, 'Actitudinal (20%)'),
    )
    DIMENSION_PESOS = {
        DIMENSION_PARCIAL: 40,
        DIMENSION_ACTIVIDADES: 40,
        DIMENSION_ACTITUDINAL: 20,
    }
    DIMENSION_LIMITES = {
        DIMENSION_PARCIAL: 100,
        DIMENSION_ACTIVIDADES: 100,
        DIMENSION_ACTITUDINAL: 100,
    }

    carga_academica = models.ForeignKey(
        CargaAcademica,
        on_delete=models.CASCADE,
        related_name='actividades'
    )
    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.CASCADE,
        related_name='actividades'
    )
    nombre = models.CharField(max_length=100)
    dimension = models.CharField(max_length=20, choices=DIMENSION_CHOICES, default=DIMENSION_ACTIVIDADES)
    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    fecha = models.DateField()
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Actividad evaluativa'
        verbose_name_plural = 'Actividades evaluativas'
        ordering = ['-fecha', 'nombre']
        indexes = [
            models.Index(fields=['carga_academica', 'periodo', 'dimension'], name='act_carga_periodo_dim_idx'),
            models.Index(fields=['carga_academica', 'periodo', '-fecha'], name='act_carga_periodo_idx'),
            models.Index(fields=['activa', '-fecha'], name='act_activa_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.carga_academica}"

    @classmethod
    def limite_dimension(cls, dimension):
        return cls.DIMENSION_LIMITES.get(dimension, 0)

    @classmethod
    def peso_dimension(cls, dimension):
        return cls.DIMENSION_PESOS.get(dimension, 0)

    def clean(self):
        errores = {}

        if self.carga_academica_id and self.periodo_id:
            if self.periodo.anio_lectivo_id != self.carga_academica.anio_lectivo_id:
                errores['periodo'] = 'El periodo academico debe pertenecer al mismo ano lectivo de la carga academica.'

        if self.fecha and self.periodo_id:
            if self.fecha < self.periodo.fecha_inicio or self.fecha > self.periodo.fecha_fin:
                errores['fecha'] = 'La fecha de la actividad debe estar dentro del rango del periodo academico.'

        if self.carga_academica_id and self.periodo_id and self.dimension and self.porcentaje is not None:
            acumulado = ActividadEvaluativa.objects.filter(
                carga_academica_id=self.carga_academica_id,
                periodo_id=self.periodo_id,
                dimension=self.dimension,
            ).exclude(pk=self.pk)
            total_actual = sum((actividad.porcentaje for actividad in acumulado), 0)
            limite = self.limite_dimension(self.dimension)
            total_resultante = total_actual + self.porcentaje

            if total_resultante > limite:
                errores['porcentaje'] = (
                    f'Esta dimension solo permite distribuir hasta {limite}% interno. '
                    f'Ya tienes {total_actual}% registrado y esta actividad dejaria {total_resultante}%.'
                )

        if errores:
            raise ValidationError(errores)


class Calificacion(models.Model):
    actividad = models.ForeignKey(
        ActividadEvaluativa,
        on_delete=models.CASCADE,
        related_name='calificaciones'
    )
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='calificaciones'
    )
    nota = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    observacion = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'
        ordering = ['estudiante__apellidos']
        unique_together = ('actividad', 'estudiante')
        indexes = [
            models.Index(fields=['actividad', 'estudiante'], name='calif_actividad_est_idx'),
            models.Index(fields=['estudiante', '-fecha_registro'], name='calif_estudiante_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.estudiante} - {self.actividad.nombre} - {self.nota}"

    def clean(self):
        if self.estudiante_id and self.actividad_id:
            if self.estudiante.grupo_id != self.actividad.carga_academica.grupo_id:
                raise ValidationError(
                    {'estudiante': 'El estudiante no pertenece al grupo asociado a esta actividad.'}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
