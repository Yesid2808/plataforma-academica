from django.urls import path
from . import views

urlpatterns = [
    path('registrar/', views.registrar_asistencia, name='registrar_asistencia'),
    path('resumen/', views.resumen_asistencia, name='resumen_asistencia'),
    path('resumen/exportar/excel/', views.exportar_resumen_asistencia_excel, name='exportar_resumen_asistencia_excel'),
]
