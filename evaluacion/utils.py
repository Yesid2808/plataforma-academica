from decimal import Decimal, ROUND_HALF_UP

from .models import ActividadEvaluativa


DOS_DECIMALES = Decimal('0.01')
CIEN = Decimal('100')


def _to_decimal(value):
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def resumir_calificaciones_por_dimension(calificaciones):
    resumen = {}

    for calificacion in calificaciones:
        dimension = calificacion.actividad.dimension
        item = resumen.setdefault(dimension, {
            'dimension': dimension,
            'etiqueta': dict(ActividadEvaluativa.DIMENSION_CHOICES).get(dimension, dimension),
            'peso_dimension': Decimal(str(ActividadEvaluativa.peso_dimension(dimension))),
            'limite_dimension': Decimal(str(ActividadEvaluativa.limite_dimension(dimension))),
            'suma_ponderada': Decimal('0'),
            'total_porcentaje': Decimal('0'),
            'notas': [],
        })
        nota = _to_decimal(calificacion.nota)
        porcentaje = _to_decimal(calificacion.actividad.porcentaje)
        item['notas'].append(nota)
        item['suma_ponderada'] += nota * porcentaje
        item['total_porcentaje'] += porcentaje

    for item in resumen.values():
        total_notas = len(item['notas'])
        if item['total_porcentaje'] > 0:
            promedio = item['suma_ponderada'] / item['total_porcentaje']
        else:
            promedio = sum(item['notas'], Decimal('0')) / Decimal(total_notas) if total_notas else Decimal('0')
        item['promedio'] = promedio.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
        item['porcentaje_registrado'] = item['total_porcentaje'].quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
        item['aporte'] = ((item['promedio'] * item['peso_dimension']) / CIEN).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
        item['cantidad'] = total_notas

    return resumen


def calcular_promedio_dimensionado(calificaciones):
    resumen = resumir_calificaciones_por_dimension(calificaciones)
    if not resumen:
        return None, {}

    peso_registrado = sum((item['peso_dimension'] for item in resumen.values()), Decimal('0'))
    if peso_registrado == 0:
        return None, resumen

    aporte_total = sum((item['aporte'] for item in resumen.values()), Decimal('0'))
    promedio = ((aporte_total / peso_registrado) * CIEN).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)
    return promedio, resumen
