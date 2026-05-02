from .models import AuditoriaCambio


def registrar_auditoria_cambio(
    *,
    actor,
    tipo,
    accion,
    modulo,
    titulo,
    descripcion,
    estudiante=None,
    grupo='',
    asignatura='',
    fecha_referencia=None,
    valor_anterior='',
    valor_nuevo='',
    referencia_url='',
    datos_extra=None,
):
    datos_extra = datos_extra or {}

    return AuditoriaCambio.objects.create(
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        tipo=tipo,
        accion=accion,
        modulo=modulo,
        titulo=titulo,
        descripcion=descripcion,
        estudiante_codigo=getattr(estudiante, 'codigo', '') or '',
        estudiante_nombre=(
            f'{getattr(estudiante, "apellidos", "")} {getattr(estudiante, "nombres", "")}'.strip()
            if estudiante else ''
        ),
        grupo=grupo,
        asignatura=asignatura,
        fecha_referencia=fecha_referencia,
        valor_anterior=str(valor_anterior or ''),
        valor_nuevo=str(valor_nuevo or ''),
        referencia_url=referencia_url or None,
        datos_extra=datos_extra,
    )
