from django.urls import path

from . import views

urlpatterns = [
    path('actividades/', views.lista_actividades, name='lista_actividades'),
    path('actividades/crear/', views.crear_actividad, name='crear_actividad'),
    path('actividades/<int:pk>/editar/', views.editar_actividad, name='editar_actividad'),
    path('actividades/<int:pk>/eliminar/', views.eliminar_actividad, name='eliminar_actividad'),
    path('actividades/<int:pk>/calificaciones/', views.registrar_calificaciones, name='registrar_calificaciones'),
    path('resumen/', views.resumen_calificaciones, name='resumen_calificaciones'),
    path('resumen/exportar/excel/', views.exportar_resumen_calificaciones_excel, name='exportar_resumen_calificaciones_excel'),
]
