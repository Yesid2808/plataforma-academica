from django.core.exceptions import ValidationError
from django.db import models
from academico.models import Estudiante, CargaAcademica


class Asistencia(models.Model):
    ESTADO_CHOICES = (
        ('P', 'Presente'),
        ('A', 'Ausente'),
        ('T', 'Tarde'),
        ('J', 'Justificado'),
    )

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='asistencias'
    )
    carga_academica = models.ForeignKey(
        CargaAcademica,
        on_delete=models.CASCADE,
        related_name='asistencias'
    )
    fecha = models.DateField()
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default='P')
    observacion = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering = ['-fecha', 'estudiante__apellidos']
        unique_together = ('estudiante', 'carga_academica', 'fecha')
        indexes = [
            models.Index(fields=['carga_academica', 'fecha'], name='asis_carga_fecha_idx'),
            models.Index(fields=['estudiante', 'fecha'], name='asis_estudiante_fecha_idx'),
            models.Index(fields=['estado', 'fecha'], name='asis_estado_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.estudiante} - {self.fecha} - {self.get_estado_display()}"

    def clean(self):
        if self.estudiante_id and self.carga_academica_id:
            if self.estudiante.grupo_id != self.carga_academica.grupo_id:
                raise ValidationError(
                    {'estudiante': 'El estudiante no pertenece al grupo asociado a esta carga academica.'}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
