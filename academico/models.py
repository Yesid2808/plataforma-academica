from django.core.exceptions import ValidationError
from django.db import models
from usuarios.models import Usuario


class AnioLectivo(models.Model):
    anio = models.PositiveIntegerField(unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Año lectivo'
        verbose_name_plural = 'Años lectivos'
        ordering = ['-anio']

    def __str__(self):
        return str(self.anio)


class PeriodoAcademico(models.Model):
    nombre = models.CharField(max_length=50)
    numero = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    anio_lectivo = models.ForeignKey(
        AnioLectivo,
        on_delete=models.CASCADE,
        related_name='periodos'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Periodo académico'
        verbose_name_plural = 'Periodos académicos'
        ordering = ['anio_lectivo', 'numero']
        unique_together = ('numero', 'anio_lectivo')

    def __str__(self):
        return f"{self.nombre} - {self.anio_lectivo.anio}"


class Grado(models.Model):
    nombre = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Grupo(models.Model):
    nombre = models.CharField(max_length=10)
    grado = models.ForeignKey(
        Grado,
        on_delete=models.CASCADE,
        related_name='grupos'
    )
    director_grupo = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'rol': 'DOC'},
        related_name='grupos_dirigidos'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('nombre', 'grado')
        ordering = ['grado__nombre', 'nombre']

    def __str__(self):
        return f"{self.grado.nombre} - {self.nombre}"


class Asignatura(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    intensidad_horaria = models.PositiveSmallIntegerField(default=1)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Estudiante(models.Model):
    TIPO_DOCUMENTO_CHOICES = (
        ('TI', 'Tarjeta de identidad'),
        ('CC', 'Cédula de ciudadanía'),
        ('RC', 'Registro civil'),
        ('CE', 'Cédula de extranjería'),
    )
    GENERO_CHOICES = (
        ('M', 'Hombre'),
        ('F', 'Mujer'),
    )

    codigo = models.CharField(max_length=20, unique=True, editable=False)
    tipo_documento = models.CharField(max_length=2, choices=TIPO_DOCUMENTO_CHOICES, default='TI')
    documento = models.CharField(max_length=20, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES, default='M')
    fecha_nacimiento = models.DateField()
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.PROTECT,
        related_name='estudiantes'
    )
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='perfil_estudiante',
        limit_choices_to={'rol': 'EST'},
    )

    foto = models.ImageField(upload_to='estudiantes/', blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)

    acudiente = models.CharField(max_length=150)
    correo_acudiente = models.EmailField(blank=True, null=True)
    telefono_acudiente = models.CharField(max_length=20)
    whatsapp_acudiente = models.CharField(max_length=20, blank=True, null=True)

    direccion = models.CharField(max_length=200, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['apellidos', 'nombres']
        indexes = [
            models.Index(fields=['grupo', 'activo'], name='est_grupo_activo_idx'),
            models.Index(fields=['apellidos', 'nombres'], name='est_nombre_idx'),
        ]

    def __str__(self):
        return f"{self.apellidos} {self.nombres}"

    def generar_codigo(self):
        ultimo = Estudiante.objects.order_by('-codigo').first()

        if not ultimo:
            return "EST-00001"

        numero = int(ultimo.codigo.split('-')[1]) + 1
        return f"EST-{numero:05d}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo()
        super().save(*args, **kwargs)

class CargaAcademica(models.Model):
    docente = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        limit_choices_to={'rol': 'DOC'},
        related_name='cargas_academicas'
    )
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name='cargas_academicas'
    )
    asignatura = models.ForeignKey(
        Asignatura,
        on_delete=models.CASCADE,
        related_name='cargas_academicas'
    )
    anio_lectivo = models.ForeignKey(
        AnioLectivo,
        on_delete=models.CASCADE,
        related_name='cargas_academicas'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('docente', 'grupo', 'asignatura', 'anio_lectivo')
        verbose_name = 'Carga académica'
        verbose_name_plural = 'Cargas académicas'
        indexes = [
            models.Index(fields=['docente', 'activo'], name='carga_docente_activa_idx'),
            models.Index(fields=['grupo', 'activo'], name='carga_grupo_activa_idx'),
            models.Index(fields=['anio_lectivo', 'activo'], name='carga_anio_activa_idx'),
        ]

    def __str__(self):
        return f"{self.asignatura.nombre} - {self.grupo} - {self.docente.get_full_name() or self.docente.username}"


class HorarioClase(models.Model):
    DIA_CHOICES = (
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miercoles'),
        (4, 'Jueves'),
        (5, 'Viernes'),
    )

    carga_academica = models.ForeignKey(
        CargaAcademica,
        on_delete=models.CASCADE,
        related_name='horarios'
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DIA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    aula = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['dia_semana', 'hora_inicio', 'carga_academica__grupo__grado__nombre', 'carga_academica__grupo__nombre']
        verbose_name = 'Horario de clase'
        verbose_name_plural = 'Horarios de clase'

    def __str__(self):
        return (
            f"{self.get_dia_semana_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M} - "
            f"{self.carga_academica.asignatura.nombre} - {self.carga_academica.grupo}"
        )

    def clean(self):
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError({'hora_fin': 'La hora de fin debe ser posterior a la hora de inicio.'})

        anio_lectivo_id = getattr(self.carga_academica, 'anio_lectivo_id', None)
        cruces = HorarioClase.objects.filter(
            dia_semana=self.dia_semana,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        ).exclude(pk=self.pk).select_related(
            'carga_academica',
            'carga_academica__grupo',
            'carga_academica__docente',
            'carga_academica__anio_lectivo',
        )

        if anio_lectivo_id:
            cruces = cruces.filter(carga_academica__anio_lectivo_id=anio_lectivo_id)

        conflicto_grupo = cruces.filter(carga_academica__grupo=self.carga_academica.grupo).first()
        if conflicto_grupo:
            raise ValidationError(
                'El grupo ya tiene una clase asignada en ese bloque horario.'
            )

        conflicto_docente = cruces.filter(carga_academica__docente=self.carga_academica.docente).first()
        if conflicto_docente:
            raise ValidationError(
                'El docente ya tiene una clase asignada en ese bloque horario.'
            )

        aula = (self.aula or '').strip()
        if aula:
            conflicto_aula = cruces.filter(aula__iexact=aula).first()
            if conflicto_aula:
                raise ValidationError(
                    {'aula': 'El aula ya esta ocupada en ese bloque horario.'}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ReporteAcudiente(models.Model):
    ESTADO_CHOICES = (
        ('ENVIADO', 'Enviado'),
        ('ERROR', 'Error'),
        ('DESCARGADO', 'Descargado'),
    )
    PERIODO_CHOICES = (
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
    )

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='reportes_generados'
    )
    periodo = models.CharField(max_length=10, choices=PERIODO_CHOICES)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    destinatario = models.EmailField(blank=True, null=True)
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES)
    enviado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reportes_enviados'
    )
    asunto = models.CharField(max_length=200, blank=True)
    mensaje_error = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Reporte a acudiente'
        verbose_name_plural = 'Reportes a acudientes'
        indexes = [
            models.Index(fields=['estudiante', 'periodo', '-fecha_registro'], name='reporte_est_periodo_idx'),
            models.Index(fields=['estado', '-fecha_registro'], name='reporte_estado_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.estudiante} - {self.periodo} - {self.estado}"
