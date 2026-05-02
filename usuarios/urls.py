from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path(
        'cambiar-contrasena/',
        auth_views.PasswordChangeView.as_view(
            template_name='usuarios/password_change.html',
            success_url='/usuarios/cambiar-contrasena/listo/',
        ),
        name='password_change',
    ),
    path(
        'cambiar-contrasena/listo/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='usuarios/password_change_done.html',
        ),
        name='password_change_done',
    ),
    path('notificaciones/', views.lista_notificaciones, name='lista_notificaciones'),
    path('notificaciones/marcar-leidas/', views.marcar_notificaciones_leidas, name='marcar_notificaciones_leidas'),
    path('notificaciones/<int:pk>/leer/', views.leer_notificacion, name='leer_notificacion'),
]
