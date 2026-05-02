from usuarios.models import NotificacionUsuario


def notificaciones_usuario(request):
    if not request.user.is_authenticated:
        return {
            'notificaciones_no_leidas': 0,
            'notificaciones_recientes': [],
            'nombre_sesion': '',
        }

    recientes = list(
        NotificacionUsuario.objects.filter(usuario=request.user)
        .select_related('actor')[:5]
    )
    nombre = request.user.get_full_name().strip() or request.user.username
    return {
        'notificaciones_no_leidas': NotificacionUsuario.objects.filter(usuario=request.user, leida=False).count(),
        'notificaciones_recientes': recientes,
        'nombre_sesion': nombre,
    }
