from django.urls import path
from . import views

urlpatterns = [
    path('horarios/', views.horarios_academicos, name='horarios_academicos'),
    path('seguimiento/', views.gestion_seguimiento, name='gestion_seguimiento'),
    path('mi-seguimiento/', views.mi_seguimiento_estudiante, name='mi_seguimiento_estudiante'),
    path('reportes/', views.gestion_reportes, name='gestion_reportes'),
    path('reportes/enviar-masivo/', views.enviar_reportes_masivos, name='enviar_reportes_masivos'),
    path('reportes/probar-correo/', views.probar_correo_reportes, name='probar_correo_reportes'),
    path('gestion/', views.gestion_academica, name='gestion_academica'),
    path('gestion/<str:catalogo>/', views.lista_catalogo, name='lista_catalogo'),
    path('gestion/<str:catalogo>/crear/', views.crear_catalogo, name='crear_catalogo'),
    path('gestion/<str:catalogo>/<int:pk>/editar/', views.editar_catalogo, name='editar_catalogo'),
    path('gestion/<str:catalogo>/<int:pk>/eliminar/', views.eliminar_catalogo, name='eliminar_catalogo'),
    path('estudiantes/', views.lista_estudiantes, name='lista_estudiantes'),
    path('estudiantes/mi-perfil/', views.mi_perfil_estudiante, name='mi_perfil_estudiante'),
    path('estudiantes/crear/', views.crear_estudiante, name='crear_estudiante'),
    path('estudiantes/<int:pk>/', views.detalle_estudiante, name='detalle_estudiante'),
    path('estudiantes/<int:pk>/reporte/', views.reporte_estudiante, name='reporte_estudiante'),
    path('estudiantes/<int:pk>/reporte/<str:periodo>/descargar/', views.descargar_reporte_estudiante, name='descargar_reporte_estudiante'),
    path('estudiantes/<int:pk>/reporte/<str:periodo>/enviar/', views.enviar_reporte_estudiante, name='enviar_reporte_estudiante'),
    path('estudiantes/<int:pk>/editar/', views.editar_estudiante, name='editar_estudiante'),
    path('estudiantes/<int:pk>/eliminar/', views.eliminar_estudiante, name='eliminar_estudiante'),
    path('estudiantes/exportar/excel/', views.exportar_estudiantes_excel, name='exportar_estudiantes_excel'),
    path('estudiantes/importar/', views.importar_estudiantes, name='importar_estudiantes'),
    path('estudiantes/<int:pk>/reactivar/', views.reactivar_estudiante, name='reactivar_estudiante'),
    path('estudiantes/plantilla/excel/', views.descargar_plantilla_estudiantes, name='descargar_plantilla_estudiantes'),
]
