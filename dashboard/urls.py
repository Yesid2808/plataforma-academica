from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('exportar-riesgo/excel/', views.exportar_estudiantes_riesgo_excel, name='exportar_estudiantes_riesgo_excel'),
]
