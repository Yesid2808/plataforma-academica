from django.contrib import admin
from .models import Asistencia


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'carga_academica', 'fecha', 'estado')
    list_filter = ('estado', 'fecha', 'carga_academica')
    search_fields = ('estudiante__nombres', 'estudiante__apellidos', 'estudiante__codigo')