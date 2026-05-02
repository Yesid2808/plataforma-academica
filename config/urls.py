from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = 'Plataforma Academica'
admin.site.site_title = 'Administracion academica'
admin.site.index_title = 'Gestion institucional y configuracion'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('academico/', include('academico.urls')),
    path('asistencia/', include('asistencia.urls')),
    path('alertas/', include('alertas.urls')),
    path('evaluacion/', include('evaluacion.urls')),
]

handler403 = 'usuarios.views.permission_denied_view'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
