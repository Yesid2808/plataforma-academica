from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

from usuarios.models import NotificacionUsuario, Usuario


def usuarios_receptores_cambios_docentes():
    return Usuario.objects.filter(rol__in=['ADMIN', 'COORD']).distinct()


def _usuarios_receptores_unicos(actor):
    receptores = list(usuarios_receptores_cambios_docentes().exclude(pk=actor.pk))

    # El docente que realiza el cambio tambien recibe la notificacion para
    # confirmar que la modificacion quedo registrada en el sistema.
    receptores.append(actor)

    receptores_unicos = []
    vistos = set()
    for receptor in receptores:
        if receptor.pk in vistos:
            continue
        vistos.add(receptor.pk)
        receptores_unicos.append(receptor)

    return receptores_unicos


def _enviar_correos_cambio_docente(*, actor, receptores, tipo, titulo, mensaje, url='', detalle_cambios=None, metadata=None):
    detalle_cambios = detalle_cambios or []
    metadata = metadata or {}

    correos_destino = [receptor for receptor in receptores if getattr(receptor, 'email', '')]
    if not correos_destino:
        return 0

    actor_nombre = actor.get_full_name() or actor.username
    asunto = f'[Seguridad academica] {titulo}'
    connection = get_connection(fail_silently=True)
    mensajes = []

    for receptor in correos_destino:
        contexto = {
            'receptor': receptor,
            'actor': actor,
            'actor_nombre': actor_nombre,
            'tipo': tipo,
            'titulo': titulo,
            'mensaje': mensaje,
            'url': url,
            'detalle_cambios': detalle_cambios,
            'metadata': metadata,
            'site_name': 'Colegio App',
        }
        cuerpo_texto = render_to_string('usuarios/email/cambio_docente.txt', contexto)
        cuerpo_html = render_to_string('usuarios/email/cambio_docente.html', contexto)
        email = EmailMultiAlternatives(
            subject=asunto,
            body=cuerpo_texto,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            to=[receptor.email],
            connection=connection,
        )
        email.attach_alternative(cuerpo_html, 'text/html')
        mensajes.append(email)

    if not mensajes:
        return 0

    return connection.send_messages(mensajes) or 0


def crear_notificaciones_docentes(actor, tipo, titulo, mensaje, url='', detalle_cambios=None, metadata=None):
    if getattr(actor, 'rol', None) != 'DOC':
        return 0

    receptores_unicos = _usuarios_receptores_unicos(actor)

    notificaciones = [
        NotificacionUsuario(
            usuario=receptor,
            actor=actor,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            url=url or None,
        )
        for receptor in receptores_unicos
    ]
    if notificaciones:
        NotificacionUsuario.objects.bulk_create(notificaciones)

    _enviar_correos_cambio_docente(
        actor=actor,
        receptores=receptores_unicos,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        url=url,
        detalle_cambios=detalle_cambios,
        metadata=metadata,
    )

    return len(notificaciones)
