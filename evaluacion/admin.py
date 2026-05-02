from django.contrib import admin
from .models import ActividadEvaluativa, Calificacion


@admin.register(ActividadEvaluativa)
class ActividadEvaluativaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'carga_academica', 'periodo', 'porcentaje', 'fecha', 'activa')
    list_filter = ('periodo', 'activa')
    search_fields = ('nombre',)


@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'actividad', 'nota')
    list_filter = ('actividad',)
    search_fields = ('estudiante__nombres', 'estudiante__apellidos', 'estudiante__codigo')