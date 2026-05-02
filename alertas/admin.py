from django.contrib import admin
from .models import AlertaTemprana, ConfiguracionAlerta, SeguimientoAlerta, TipoAlerta


@admin.register(TipoAlerta)
class TipoAlertaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)


@admin.register(ConfiguracionAlerta)
class ConfiguracionAlertaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_alerta', 'operador', 'umbral', 'nivel', 'activa')
    list_filter = ('tipo_alerta', 'nivel', 'activa')
    search_fields = ('nombre',)


@admin.register(AlertaTemprana)
class AlertaTempranaAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'tipo_alerta', 'nivel', 'estado', 'fecha_generacion')
    list_filter = ('tipo_alerta', 'nivel', 'estado')
    search_fields = (
        'estudiante__nombres',
        'estudiante__apellidos',
        'estudiante__codigo',
        'descripcion',
    )


@admin.register(SeguimientoAlerta)
class SeguimientoAlertaAdmin(admin.ModelAdmin):
    list_display = ('alerta', 'accion', 'resultado', 'registrado_por', 'fecha_registro', 'proxima_revision')
    list_filter = ('accion', 'resultado', 'fecha_registro')
    search_fields = (
        'alerta__estudiante__nombres',
        'alerta__estudiante__apellidos',
        'alerta__estudiante__codigo',
        'descripcion',
    )
    autocomplete_fields = ('alerta', 'registrado_por')
