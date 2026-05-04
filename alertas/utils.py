from decimal import Decimal

from asistencia.models import Asistencia
from evaluacion.models import Calificacion
from evaluacion.utils import calcular_promedio_dimensionado
from .models import AlertaTemprana, ConfiguracionAlerta, TipoAlerta


INASISTENCIA_ACUMULADA = 'Inasistencia acumulada'
BAJO_RENDIMIENTO = 'Bajo rendimiento academico'
RIESGO_INTEGRAL = 'Riesgo integral academico'
CAIDA_RENDIMIENTO = 'Caida de rendimiento academico'
RIESGO_MULTIMATERIA = 'Riesgo por multiples materias'

_CONFIG_INASISTENCIA_READY = False
_CONFIG_ALERTAS_ACADEMICAS_READY = False


def comparar_valor(valor, operador, umbral):
    valor = Decimal(str(valor))
    umbral = Decimal(str(umbral))

    if operador == '>=':
        return valor >= umbral
    if operador == '>':
        return valor > umbral
    if operador == '<=':
        return valor <= umbral
    if operador == '<':
        return valor < umbral
    if operador == '==':
        return valor == umbral
    return False


def obtener_promedio_academico(estudiante):
    calificaciones = list(Calificacion.objects.filter(estudiante=estudiante).select_related('actividad'))
    promedio, _ = calcular_promedio_dimensionado(calificaciones)
    if promedio is None:
        return None
    return promedio.quantize(Decimal('0.01'))


def obtener_total_ausencias(estudiante):
    total_cache = getattr(estudiante, '_total_ausencias_cache', None)
    if total_cache is not None:
        return total_cache
    return Asistencia.objects.filter(estudiante=estudiante, estado='A').count()


def obtener_detalle_inasistencias(estudiante):
    return list(
        Asistencia.objects.select_related(
            'carga_academica',
            'carga_academica__asignatura',
        ).filter(
            estudiante=estudiante,
            estado='A',
        ).order_by('-fecha', 'carga_academica__asignatura__nombre')
    )


def obtener_materias_en_riesgo(estudiante):
    promedios = {}
    for calificacion in Calificacion.objects.select_related(
        'actividad',
        'actividad__carga_academica',
        'actividad__carga_academica__asignatura',
    ).filter(estudiante=estudiante):
        asignatura_id = calificacion.actividad.carga_academica.asignatura_id
        item = promedios.setdefault(asignatura_id, {
            'nombre': calificacion.actividad.carga_academica.asignatura.nombre,
            'calificaciones': [],
        })
        item['calificaciones'].append(calificacion)

    materias = []
    for item in promedios.values():
        promedio, _ = calcular_promedio_dimensionado(item['calificaciones'])
        if promedio is not None and promedio < Decimal('3.00'):
            materias.append((item['nombre'], promedio.quantize(Decimal('0.01'))))
    return materias


def obtener_detalle_materias(estudiante):
    promedios = {}
    for calificacion in Calificacion.objects.select_related(
        'actividad',
        'actividad__carga_academica',
        'actividad__carga_academica__asignatura',
    ).filter(estudiante=estudiante):
        asignatura_id = calificacion.actividad.carga_academica.asignatura_id
        item = promedios.setdefault(asignatura_id, {
            'nombre': calificacion.actividad.carga_academica.asignatura.nombre,
            'calificaciones': [],
        })
        item['calificaciones'].append(calificacion)

    materias = []
    for item in promedios.values():
        promedio, resumen_dimensiones = calcular_promedio_dimensionado(item['calificaciones'])
        if promedio is None:
            continue
        materias.append({
            'nombre': item['nombre'],
            'promedio': promedio.quantize(Decimal('0.01')),
            'cantidad': len(item['calificaciones']),
            'resumen_dimensiones': resumen_dimensiones,
        })

    return sorted(materias, key=lambda item: (item['promedio'], item['nombre']))


def obtener_caida_reciente(estudiante):
    calificaciones = list(
        Calificacion.objects.filter(estudiante=estudiante).order_by('-fecha_registro')[:6]
    )
    if len(calificaciones) < 4:
        return None

    recientes = calificaciones[:3]
    anteriores = calificaciones[3:6]
    promedio_reciente = sum(c.nota for c in recientes) / Decimal(len(recientes))
    promedio_anterior = sum(c.nota for c in anteriores) / Decimal(len(anteriores))
    caida = promedio_anterior - promedio_reciente
    return {
        'promedio_reciente': promedio_reciente.quantize(Decimal('0.01')),
        'promedio_anterior': promedio_anterior.quantize(Decimal('0.01')),
        'caida': caida.quantize(Decimal('0.01')),
    }


def obtener_detalle_caida_reciente(estudiante):
    return list(
        Calificacion.objects.select_related(
            'actividad',
            'actividad__carga_academica',
            'actividad__carga_academica__asignatura',
        ).filter(estudiante=estudiante).order_by('-fecha_registro')[:6]
    )


def _obtener_configuracion(tipo_alerta, valor):
    configuracion_aplicada = None

    for config in ConfiguracionAlerta.objects.filter(tipo_alerta=tipo_alerta, activa=True).order_by('umbral'):
        if comparar_valor(valor, config.operador, config.umbral):
            configuracion_aplicada = config

    return configuracion_aplicada


def _guardar_o_reabrir_alerta(estudiante, tipo_alerta, configuracion, nivel, descripcion):
    alerta_existente = AlertaTemprana.objects.filter(
        estudiante=estudiante,
        tipo_alerta=tipo_alerta
    ).exclude(estado='CERRADA').first()

    if alerta_existente:
        alerta_existente.configuracion = configuracion
        alerta_existente.nivel = nivel
        alerta_existente.descripcion = descripcion
        alerta_existente.estado = 'ACTIVA'
        alerta_existente.save()
        return alerta_existente

    alerta_cerrada = AlertaTemprana.objects.filter(
        estudiante=estudiante,
        tipo_alerta=tipo_alerta,
        estado='CERRADA'
    ).order_by('-fecha_generacion').first()

    if alerta_cerrada:
        alerta_cerrada.configuracion = configuracion
        alerta_cerrada.nivel = nivel
        alerta_cerrada.descripcion = descripcion
        alerta_cerrada.estado = 'ACTIVA'
        alerta_cerrada.save()
        return alerta_cerrada

    return AlertaTemprana.objects.create(
        estudiante=estudiante,
        tipo_alerta=tipo_alerta,
        configuracion=configuracion,
        nivel=nivel,
        descripcion=descripcion,
        estado='ACTIVA',
    )


def _cerrar_alerta_si_existe(estudiante, tipo_alerta, descripcion):
    alerta_existente = AlertaTemprana.objects.filter(
        estudiante=estudiante,
        tipo_alerta=tipo_alerta
    ).exclude(estado='CERRADA').first()

    if alerta_existente:
        alerta_existente.estado = 'CERRADA'
        alerta_existente.descripcion = descripcion
        alerta_existente.save()
        return alerta_existente

    return None


def asegurar_configuraciones_inasistencia():
    global _CONFIG_INASISTENCIA_READY
    if _CONFIG_INASISTENCIA_READY and TipoAlerta.objects.filter(nombre=INASISTENCIA_ACUMULADA).exists():
        return

    tipo_alerta, _ = TipoAlerta.objects.get_or_create(
        nombre=INASISTENCIA_ACUMULADA,
        defaults={
            'descripcion': 'Alerta por ausencias acumuladas del estudiante.',
            'activo': True,
        }
    )

    configuraciones = [
        ('Atencion por inasistencia', '>=', Decimal('2.00'), 'ATENCION'),
        ('Riesgo por inasistencia', '>=', Decimal('3.00'), 'RIESGO'),
        ('Critico por inasistencia', '>=', Decimal('5.00'), 'CRITICO'),
    ]

    for nombre, operador, umbral, nivel in configuraciones:
        ConfiguracionAlerta.objects.get_or_create(
            tipo_alerta=tipo_alerta,
            nombre=nombre,
            defaults={
                'operador': operador,
                'umbral': umbral,
                'nivel': nivel,
                'activa': True,
                'descripcion': f'Se activa con {operador} {umbral} ausencias.',
            }
        )
    _CONFIG_INASISTENCIA_READY = True


def asegurar_configuraciones_alertas_academicas():
    global _CONFIG_ALERTAS_ACADEMICAS_READY
    if _CONFIG_ALERTAS_ACADEMICAS_READY and TipoAlerta.objects.filter(nombre=BAJO_RENDIMIENTO).exists():
        return

    tipo_rendimiento, _ = TipoAlerta.objects.get_or_create(
        nombre=BAJO_RENDIMIENTO,
        defaults={
            'descripcion': 'Alerta por promedio academico inferior al umbral institucional.',
            'activo': True,
        }
    )
    ConfiguracionAlerta.objects.get_or_create(
        tipo_alerta=tipo_rendimiento,
        nombre='Promedio inferior a 3.0',
        defaults={
            'operador': '<',
            'umbral': Decimal('3.00'),
            'nivel': 'RIESGO',
            'activa': True,
            'descripcion': 'Se activa cuando el promedio academico acumulado es inferior a 3.0.',
        }
    )

    tipo_integral, _ = TipoAlerta.objects.get_or_create(
        nombre=RIESGO_INTEGRAL,
        defaults={
            'descripcion': 'Alerta por combinacion de bajo rendimiento e inasistencia.',
            'activo': True,
        }
    )
    ConfiguracionAlerta.objects.get_or_create(
        tipo_alerta=tipo_integral,
        nombre='Promedio bajo y ausencias acumuladas',
        defaults={
            'operador': '>=',
            'umbral': Decimal('1.00'),
            'nivel': 'CRITICO',
            'activa': True,
            'descripcion': 'Se activa si el estudiante tiene promedio inferior a 3.0 y al menos 3 ausencias.',
        }
    )

    tipo_caida, _ = TipoAlerta.objects.get_or_create(
        nombre=CAIDA_RENDIMIENTO,
        defaults={
            'descripcion': 'Alerta por disminucion sostenida del promedio reciente del estudiante.',
            'activo': True,
        }
    )
    ConfiguracionAlerta.objects.get_or_create(
        tipo_alerta=tipo_caida,
        nombre='Caida reciente igual o superior a 1.00',
        defaults={
            'operador': '>=',
            'umbral': Decimal('1.00'),
            'nivel': 'ATENCION',
            'activa': True,
            'descripcion': 'Se activa cuando el promedio reciente cae 1.00 o mas frente al bloque anterior.',
        }
    )

    tipo_multimateria, _ = TipoAlerta.objects.get_or_create(
        nombre=RIESGO_MULTIMATERIA,
        defaults={
            'descripcion': 'Alerta por bajo rendimiento en varias asignaturas al mismo tiempo.',
            'activo': True,
        }
    )
    ConfiguracionAlerta.objects.get_or_create(
        tipo_alerta=tipo_multimateria,
        nombre='Dos o mas asignaturas en riesgo',
        defaults={
            'operador': '>=',
            'umbral': Decimal('2.00'),
            'nivel': 'CRITICO',
            'activa': True,
            'descripcion': 'Se activa cuando el estudiante tiene dos o mas asignaturas con promedio inferior a 3.0.',
        }
    )
    _CONFIG_ALERTAS_ACADEMICAS_READY = True


def evaluar_alerta_inasistencia(estudiante):
    asegurar_configuraciones_inasistencia()

    try:
        tipo_alerta = TipoAlerta.objects.get(nombre=INASISTENCIA_ACUMULADA, activo=True)
    except TipoAlerta.DoesNotExist:
        return None

    total_ausencias = obtener_total_ausencias(estudiante)
    configuracion = _obtener_configuracion(tipo_alerta, total_ausencias)

    if configuracion:
        descripcion = f'El estudiante registra {total_ausencias} inasistencias acumuladas.'
        return _guardar_o_reabrir_alerta(
            estudiante,
            tipo_alerta,
            configuracion,
            configuracion.nivel,
            descripcion
        )

    return _cerrar_alerta_si_existe(
        estudiante,
        tipo_alerta,
        f'El estudiante ya no cumple la condicion de inasistencia acumulada. Total actual: {total_ausencias}.'
    )


def evaluar_alerta_bajo_rendimiento(estudiante):
    asegurar_configuraciones_alertas_academicas()

    try:
        tipo_alerta = TipoAlerta.objects.get(nombre=BAJO_RENDIMIENTO, activo=True)
    except TipoAlerta.DoesNotExist:
        return None

    promedio = obtener_promedio_academico(estudiante)
    if promedio is None:
        return _cerrar_alerta_si_existe(
            estudiante,
            tipo_alerta,
            'El estudiante no tiene calificaciones registradas actualmente.'
        )

    configuracion = _obtener_configuracion(tipo_alerta, promedio)

    if configuracion:
        descripcion = f'El estudiante registra promedio academico acumulado de {promedio}.'
        return _guardar_o_reabrir_alerta(
            estudiante,
            tipo_alerta,
            configuracion,
            configuracion.nivel,
            descripcion
        )

    return _cerrar_alerta_si_existe(
        estudiante,
        tipo_alerta,
        f'El estudiante ya no cumple la condicion de bajo rendimiento. Promedio actual: {promedio}.'
    )


def evaluar_alerta_riesgo_integral(estudiante):
    asegurar_configuraciones_alertas_academicas()

    try:
        tipo_alerta = TipoAlerta.objects.get(nombre=RIESGO_INTEGRAL, activo=True)
    except TipoAlerta.DoesNotExist:
        return None

    promedio = obtener_promedio_academico(estudiante)
    total_ausencias = obtener_total_ausencias(estudiante)
    cumple_condicion = promedio is not None and promedio < Decimal('3.00') and total_ausencias >= 3

    if cumple_condicion:
        configuracion = ConfiguracionAlerta.objects.filter(
            tipo_alerta=tipo_alerta,
            activa=True
        ).order_by('-umbral').first()
        descripcion = (
            f'Riesgo integral: promedio academico {promedio} y '
            f'{total_ausencias} inasistencias acumuladas.'
        )
        return _guardar_o_reabrir_alerta(
            estudiante,
            tipo_alerta,
            configuracion,
            configuracion.nivel if configuracion else 'CRITICO',
            descripcion
        )

    detalle_promedio = promedio if promedio is not None else 'sin calificaciones'
    return _cerrar_alerta_si_existe(
        estudiante,
        tipo_alerta,
        f'El estudiante ya no cumple la condicion de riesgo integral. Promedio: {detalle_promedio}; ausencias: {total_ausencias}.'
    )


def evaluar_alerta_caida_rendimiento(estudiante):
    asegurar_configuraciones_alertas_academicas()
    try:
        tipo_alerta = TipoAlerta.objects.get(nombre=CAIDA_RENDIMIENTO, activo=True)
    except TipoAlerta.DoesNotExist:
        return None

    caida = obtener_caida_reciente(estudiante)
    if not caida:
        return _cerrar_alerta_si_existe(
            estudiante,
            tipo_alerta,
            'No hay suficientes calificaciones para evaluar la tendencia reciente.'
        )

    configuracion = _obtener_configuracion(tipo_alerta, caida['caida'])
    if configuracion and caida['caida'] > 0:
        descripcion = (
            f"El promedio reciente bajo de {caida['promedio_anterior']} a "
            f"{caida['promedio_reciente']} (caida {caida['caida']})."
        )
        return _guardar_o_reabrir_alerta(
            estudiante,
            tipo_alerta,
            configuracion,
            configuracion.nivel,
            descripcion
        )

    return _cerrar_alerta_si_existe(
        estudiante,
        tipo_alerta,
        f"Sin caida significativa reciente. Promedio previo: {caida['promedio_anterior']}; reciente: {caida['promedio_reciente']}."
    )


def evaluar_alerta_riesgo_multimateria(estudiante):
    asegurar_configuraciones_alertas_academicas()
    try:
        tipo_alerta = TipoAlerta.objects.get(nombre=RIESGO_MULTIMATERIA, activo=True)
    except TipoAlerta.DoesNotExist:
        return None

    materias = obtener_materias_en_riesgo(estudiante)
    total = len(materias)
    configuracion = _obtener_configuracion(tipo_alerta, total)

    if configuracion:
        detalle = ', '.join(f'{nombre} ({promedio})' for nombre, promedio in materias[:4])
        descripcion = f'El estudiante presenta {total} asignaturas en riesgo: {detalle}.'
        return _guardar_o_reabrir_alerta(
            estudiante,
            tipo_alerta,
            configuracion,
            configuracion.nivel,
            descripcion
        )

    return _cerrar_alerta_si_existe(
        estudiante,
        tipo_alerta,
        f'El estudiante no presenta multiples asignaturas en riesgo. Total actual: {total}.'
    )


def evaluar_alertas_academicas(estudiante):
    return {
        'inasistencia': evaluar_alerta_inasistencia(estudiante),
        'bajo_rendimiento': evaluar_alerta_bajo_rendimiento(estudiante),
        'riesgo_integral': evaluar_alerta_riesgo_integral(estudiante),
        'caida_rendimiento': evaluar_alerta_caida_rendimiento(estudiante),
        'riesgo_multimateria': evaluar_alerta_riesgo_multimateria(estudiante),
    }


def evaluar_alertas_por_asistencia(estudiante):
    return {
        'inasistencia': evaluar_alerta_inasistencia(estudiante),
    }


def construir_detalle_alerta(alerta):
    estudiante = alerta.estudiante
    tipo = alerta.tipo_alerta.nombre if alerta.tipo_alerta else ''

    if tipo == INASISTENCIA_ACUMULADA:
        inasistencias = obtener_detalle_inasistencias(estudiante)
        return {
            'titulo': 'Detalle de inasistencias acumuladas',
            'descripcion_actual': f'Se registran actualmente {len(inasistencias)} inasistencias acumuladas.',
            'resumen': f'Se encontraron {len(inasistencias)} inasistencias asociadas a esta alerta.',
            'metricas': [
                {'label': 'Total inasistencias', 'value': len(inasistencias)},
            ],
            'tabla': {
                'columnas': ['Fecha', 'Asignatura', 'Estado', 'Observacion'],
                'filas': [
                    [
                        item.fecha.strftime('%Y-%m-%d'),
                        item.carga_academica.asignatura.nombre,
                        item.get_estado_display(),
                        item.observacion or 'Sin observacion',
                    ]
                    for item in inasistencias
                ],
            },
        }

    if tipo == BAJO_RENDIMIENTO:
        promedio = obtener_promedio_academico(estudiante)
        materias = obtener_detalle_materias(estudiante)
        materias_riesgo = [item for item in materias if item['promedio'] < Decimal('3.00')]
        descripcion_actual = (
            f'El estudiante registra promedio academico acumulado de {promedio}.'
            if promedio is not None else
            'El estudiante no tiene calificaciones registradas actualmente.'
        )
        return {
            'titulo': 'Detalle del bajo rendimiento academico',
            'descripcion_actual': descripcion_actual,
            'resumen': 'Se muestra el promedio general y el comportamiento por asignatura del estudiante.',
            'metricas': [
                {'label': 'Promedio general', 'value': promedio if promedio is not None else 'Sin notas'},
                {'label': 'Materias en riesgo', 'value': len(materias_riesgo)},
            ],
            'tabla': {
                'columnas': ['Asignatura', 'Promedio', 'Actividades', 'Estado'],
                'filas': [
                    [
                        item['nombre'],
                        str(item['promedio']),
                        item['cantidad'],
                        'En riesgo' if item['promedio'] < Decimal('3.00') else 'Estable',
                    ]
                    for item in materias
                ],
            },
        }

    if tipo == RIESGO_INTEGRAL:
        promedio = obtener_promedio_academico(estudiante)
        inasistencias = obtener_detalle_inasistencias(estudiante)
        materias = obtener_detalle_materias(estudiante)
        materias_riesgo = [item for item in materias if item['promedio'] < Decimal('3.00')]
        if promedio is not None and promedio < Decimal('3.00') and len(inasistencias) >= 3:
            descripcion_actual = (
                f'Riesgo integral: promedio academico {promedio} y '
                f'{len(inasistencias)} inasistencias acumuladas.'
            )
        else:
            detalle_promedio = promedio if promedio is not None else 'sin calificaciones'
            descripcion_actual = (
                'El estudiante ya no cumple la condicion de riesgo integral. '
                f'Promedio: {detalle_promedio}; ausencias: {len(inasistencias)}.'
            )
        return {
            'titulo': 'Detalle del riesgo integral',
            'descripcion_actual': descripcion_actual,
            'resumen': 'Esta alerta combina ausencias acumuladas con bajo rendimiento academico.',
            'metricas': [
                {'label': 'Promedio general', 'value': promedio if promedio is not None else 'Sin notas'},
                {'label': 'Inasistencias', 'value': len(inasistencias)},
                {'label': 'Materias en riesgo', 'value': len(materias_riesgo)},
            ],
            'tabla': {
                'columnas': ['Tipo', 'Detalle', 'Valor'],
                'filas': (
                    [['Inasistencia', f"{item.fecha:%Y-%m-%d} - {item.carga_academica.asignatura.nombre}", item.get_estado_display()] for item in inasistencias]
                    + [['Asignatura', item['nombre'], str(item['promedio'])] for item in materias_riesgo]
                ),
            },
        }

    if tipo == CAIDA_RENDIMIENTO:
        caida = obtener_caida_reciente(estudiante)
        detalle = obtener_detalle_caida_reciente(estudiante)
        descripcion_actual = (
            (
                f"El promedio reciente bajo de {caida['promedio_anterior']} a "
                f"{caida['promedio_reciente']} (caida {caida['caida']})."
            ) if caida else
            'No hay suficientes calificaciones para evaluar la tendencia reciente.'
        )
        return {
            'titulo': 'Detalle de la caida reciente de rendimiento',
            'descripcion_actual': descripcion_actual,
            'resumen': 'Se comparan las ultimas calificaciones registradas para evidenciar el descenso.',
            'metricas': [
                {'label': 'Promedio anterior', 'value': caida['promedio_anterior'] if caida else 'N/D'},
                {'label': 'Promedio reciente', 'value': caida['promedio_reciente'] if caida else 'N/D'},
                {'label': 'Caida', 'value': caida['caida'] if caida else 'N/D'},
            ],
            'tabla': {
                'columnas': ['Fecha registro', 'Asignatura', 'Actividad', 'Nota'],
                'filas': [
                    [
                        item.fecha_registro.strftime('%Y-%m-%d %H:%M'),
                        item.actividad.carga_academica.asignatura.nombre,
                        item.actividad.nombre,
                        str(item.nota),
                    ]
                    for item in detalle
                ],
            },
        }

    if tipo == RIESGO_MULTIMATERIA:
        materias = [item for item in obtener_detalle_materias(estudiante) if item['promedio'] < Decimal('3.00')]
        if materias:
            detalle = ', '.join(f"{item['nombre']} ({item['promedio']})" for item in materias[:4])
            descripcion_actual = f'El estudiante presenta {len(materias)} asignaturas en riesgo: {detalle}.'
        else:
            descripcion_actual = 'El estudiante no presenta multiples asignaturas en riesgo actualmente.'
        return {
            'titulo': 'Detalle de asignaturas en riesgo',
            'descripcion_actual': descripcion_actual,
            'resumen': 'Estas son las asignaturas que actualmente sostienen la alerta.',
            'metricas': [
                {'label': 'Asignaturas comprometidas', 'value': len(materias)},
            ],
            'tabla': {
                'columnas': ['Asignatura', 'Promedio', 'Actividades'],
                'filas': [
                    [item['nombre'], str(item['promedio']), item['cantidad']]
                    for item in materias
                ],
            },
        }

    return {
        'titulo': 'Soporte del caso',
        'descripcion_actual': alerta.descripcion,
        'resumen': 'Esta alerta aun no tiene un detalle estructurado adicional.',
        'metricas': [],
        'tabla': None,
    }
