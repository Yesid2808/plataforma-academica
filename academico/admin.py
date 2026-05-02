from django.contrib import admin
from .models import (
    AnioLectivo,
    PeriodoAcademico,
    Grado,
    Grupo,
    Asignatura,
    Estudiante,
    CargaAcademica,
    HorarioClase,
    ReporteAcudiente,
)

admin.site.register(AnioLectivo)
admin.site.register(PeriodoAcademico)
admin.site.register(Grado)
admin.site.register(Grupo)
admin.site.register(Asignatura)
admin.site.register(CargaAcademica)
admin.site.register(HorarioClase)
admin.site.register(ReporteAcudiente)


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'documento', 'nombres', 'apellidos', 'grupo', 'activo')
    search_fields = ('codigo', 'documento', 'nombres', 'apellidos')
    list_filter = ('activo', 'grupo')
    readonly_fields = ('codigo',)
