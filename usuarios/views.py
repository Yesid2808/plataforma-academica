from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import NotificacionUsuario
from .permissions import es_estudiante


def login_view(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    mensaje = None
    username = request.POST.get('username', '').strip() if request.method == 'POST' else ''
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    login_failed_attempts = int(request.session.get('login_failed_attempts', 0) or 0)
    lock_until_raw = request.session.get('login_locked_until')
    lock_until = None

    if lock_until_raw:
        try:
            lock_until = timezone.datetime.fromisoformat(lock_until_raw)
            if timezone.is_naive(lock_until):
                lock_until = timezone.make_aware(lock_until, timezone.get_current_timezone())
        except ValueError:
            lock_until = None
            request.session.pop('login_locked_until', None)

    if lock_until and lock_until <= timezone.now():
        request.session.pop('login_locked_until', None)
        request.session['login_failed_attempts'] = 0
        login_failed_attempts = 0
        lock_until = None

    if request.method == 'POST':
        if lock_until and lock_until > timezone.now():
            minutos_restantes = max(1, int((lock_until - timezone.now()).total_seconds() // 60) + 1)
            mensaje = f'Inicio de sesion bloqueado temporalmente. Intenta de nuevo en {minutos_restantes} minuto(s).'
            return render(request, 'usuarios/login.html', {
                'mensaje': mensaje,
                'username': username,
                'next_url': next_url,
            })

        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            request.session['login_failed_attempts'] = 0
            request.session.pop('login_locked_until', None)
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('inicio')
        login_failed_attempts += 1
        request.session['login_failed_attempts'] = login_failed_attempts

        if login_failed_attempts >= settings.LOGIN_MAX_ATTEMPTS:
            lock_until = timezone.now() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
            request.session['login_locked_until'] = lock_until.isoformat()
            mensaje = (
                f'Se bloqueo temporalmente el acceso tras varios intentos fallidos. '
                f'Intenta de nuevo en {settings.LOGIN_LOCK_MINUTES} minuto(s).'
            )
        else:
            intentos_restantes = max(settings.LOGIN_MAX_ATTEMPTS - login_failed_attempts, 0)
            mensaje = f'Usuario o contrasena incorrectos. Intentos restantes: {intentos_restantes}.'

    return render(request, 'usuarios/login.html', {
        'mensaje': mensaje,
        'username': username,
        'next_url': next_url,
    })


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def lista_notificaciones(request):
    if es_estudiante(request.user):
        raise PermissionDenied
    notificaciones = NotificacionUsuario.objects.filter(
        usuario=request.user
    ).select_related('actor').order_by('-fecha_creacion')
    return render(request, 'usuarios/notificaciones.html', {'notificaciones': notificaciones})


@login_required
def leer_notificacion(request, pk):
    if es_estudiante(request.user):
        raise PermissionDenied
    notificacion = get_object_or_404(NotificacionUsuario, pk=pk, usuario=request.user)
    if notificacion.leida is False:
        notificacion.leida = True
        notificacion.save(update_fields=['leida'])

    if notificacion.url:
        return redirect(notificacion.url)
    return redirect('lista_notificaciones')


@require_POST
@login_required
def marcar_notificaciones_leidas(request):
    if es_estudiante(request.user):
        raise PermissionDenied
    NotificacionUsuario.objects.filter(usuario=request.user, leida=False).update(leida=True)
    return redirect('lista_notificaciones')


def permission_denied_view(request, exception=None):
    return render(request, '403.html', status=403)
