from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_alertas, name='lista_alertas'),
    path('exportar/excel/', views.exportar_alertas_excel, name='exportar_alertas_excel'),
    path('<int:pk>/', views.detalle_alerta, name='detalle_alerta'),
    path('<int:pk>/estado/<str:nuevo_estado>/', views.cambiar_estado_alerta, name='cambiar_estado_alerta'),
]
