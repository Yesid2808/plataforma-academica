from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ROL_CHOICES = (
        ('ADMIN', 'Administrador'),
        ('COORD', 'Coordinador'),
        ('DOC', 'Docente'),
        ('EST', 'Estudiante'),
    )

    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='DOC')
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"


class NotificacionUsuario(models.Model):
    TIPO_CHOICES = (
        ('ASISTENCIA', 'Asistencia'),
        ('CALIFICACION', 'Calificacion'),
        ('SISTEMA', 'Sistema'),
    )

    usuario = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    actor = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificaciones_generadas'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='SISTEMA')
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    url = models.CharField(max_length=255, blank=True, null=True)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Notificacion'
        verbose_name_plural = 'Notificaciones'
        indexes = [
            models.Index(fields=['usuario', 'leida', '-fecha_creacion'], name='notif_usuario_leida_idx'),
            models.Index(fields=['tipo', '-fecha_creacion'], name='notif_tipo_fecha_idx'),
        ]

    def __str__(self):
        return f'{self.usuario.username} - {self.titulo}'


class AuditoriaCambio(models.Model):
    TIPO_CHOICES = (
        ('ASISTENCIA', 'Asistencia'),
        ('CALIFICACION', 'Calificacion'),
        ('SISTEMA', 'Sistema'),
    )
    ACCION_CHOICES = (
        ('CREACION', 'Creacion'),
        ('EDICION', 'Edicion'),
        ('ELIMINACION', 'Eliminacion'),
    )

    actor = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditorias_realizadas'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='SISTEMA')
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES, default='EDICION')
    modulo = models.CharField(max_length=50)
    titulo = models.CharField(max_length=180)
    descripcion = models.TextField()
    estudiante_codigo = models.CharField(max_length=20, blank=True)
    estudiante_nombre = models.CharField(max_length=200, blank=True)
    grupo = models.CharField(max_length=50, blank=True)
    asignatura = models.CharField(max_length=120, blank=True)
    fecha_referencia = models.DateField(null=True, blank=True)
    valor_anterior = models.CharField(max_length=255, blank=True)
    valor_nuevo = models.CharField(max_length=255, blank=True)
    referencia_url = models.CharField(max_length=255, blank=True, null=True)
    datos_extra = models.JSONField(default=dict, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Auditoria de cambio'
        verbose_name_plural = 'Auditorias de cambios'
        indexes = [
            models.Index(fields=['tipo', '-fecha_creacion'], name='audit_tipo_fecha_idx'),
            models.Index(fields=['modulo', '-fecha_creacion'], name='audit_modulo_fecha_idx'),
            models.Index(fields=['estudiante_codigo', '-fecha_creacion'], name='audit_estudiante_idx'),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.titulo}'
