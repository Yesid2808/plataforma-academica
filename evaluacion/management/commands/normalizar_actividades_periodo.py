from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from academico.models import PeriodoAcademico
from evaluacion.models import ActividadEvaluativa


CIEN = Decimal('100.00')


def repartir_porcentajes(cantidad):
    if cantidad <= 0:
        return []

    base = (CIEN / Decimal(cantidad)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    porcentajes = [base for _ in range(cantidad)]
    total = sum(porcentajes, Decimal('0.00'))
    diferencia = (CIEN - total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    porcentajes[-1] = (porcentajes[-1] + diferencia).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return porcentajes


def obtener_grado_numerico(carga):
    try:
        return int(carga.grupo.grado.nombre)
    except (TypeError, ValueError):
        return 0


def obtener_plantillas(asignatura, grado):
    asignatura_normalizada = (asignatura or '').strip().lower()
    es_basica = grado <= 7 if grado else True

    plantillas = {
        'matematicas': {
            'basica': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: operaciones y fracciones',
                    'Parcial 2: problemas de proporcionalidad',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Taller de ejercicios guiados',
                    'Quiz de procedimiento',
                    'Practica en clase',
                    'Resolucion de problemas',
                    'Sustentacion de ejercicios',
                    'Guia de refuerzo',
                    'Trabajo colaborativo',
                    'Control corto',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Participacion y disposicion en clase',
                    'Cumplimiento y orden del cuaderno',
                ],
            },
            'avanzada': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: expresiones algebraicas y ecuaciones',
                    'Parcial 2: funciones y analisis de datos',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Taller de algebra aplicada',
                    'Quiz de ecuaciones',
                    'Practica de razonamiento numerico',
                    'Resolucion de problemas contextualizados',
                    'Sustentacion de procedimientos',
                    'Guia de funciones lineales',
                    'Trabajo colaborativo de estadistica',
                    'Control de seguimiento',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Participacion y argumentacion matematica',
                    'Cumplimiento y organizacion del proceso',
                ],
            },
        },
        'lengua castellana': {
            'basica': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: comprension lectora',
                    'Parcial 2: produccion textual',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Taller de lectura guiada',
                    'Control de lectura',
                    'Produccion de cuento corto',
                    'Mapa conceptual del texto',
                    'Exposicion oral',
                    'Guia de ortografia y redaccion',
                    'Trabajo colaborativo de analisis',
                    'Revision de cuaderno',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Participacion en clase y escucha activa',
                    'Cumplimiento en entregas y presentacion',
                ],
            },
            'avanzada': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: lectura critica',
                    'Parcial 2: texto argumentativo',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Taller de analisis textual',
                    'Control de lectura critica',
                    'Resena argumentativa',
                    'Debate guiado',
                    'Exposicion oral sustentada',
                    'Guia de cohesion y coherencia',
                    'Produccion escrita en clase',
                    'Revision de portafolio',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Participacion argumentativa y escucha',
                    'Cumplimiento y calidad en las entregas',
                ],
            },
        },
        'ingles': {
            'basica': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: vocabulary and reading',
                    'Parcial 2: grammar and writing',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Vocabulary quiz',
                    'Reading workshop',
                    'Workbook practice',
                    'Speaking activity',
                    'Listening checkpoint',
                    'Class guide',
                    'Short writing task',
                    'Collaborative practice',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Class participation',
                    'Homework responsibility',
                ],
            },
            'avanzada': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: reading comprehension and vocabulary',
                    'Parcial 2: grammar use and paragraph writing',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Vocabulary checkpoint',
                    'Reading comprehension workshop',
                    'Grammar practice guide',
                    'Speaking presentation',
                    'Listening activity',
                    'Workbook follow-up',
                    'Short paragraph writing',
                    'Collaborative role play',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Class participation and speaking effort',
                    'Homework completion and responsibility',
                ],
            },
        },
        'ciencias sociales': {
            'basica': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: territorio y sociedad',
                    'Parcial 2: historia y organizacion social',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Taller de analisis social',
                    'Linea de tiempo',
                    'Mapa tematico',
                    'Quiz de seguimiento',
                    'Exposicion grupal',
                    'Guia de trabajo en clase',
                    'Lectura y preguntas',
                    'Trabajo colaborativo',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Participacion argumentativa',
                    'Cumplimiento y responsabilidad',
                ],
            },
            'avanzada': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: democracia y participacion',
                    'Parcial 2: economia y transformaciones sociales',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Taller de analisis historico',
                    'Linea de tiempo comparativa',
                    'Mapa politico tematico',
                    'Quiz de seguimiento',
                    'Exposicion sustentada',
                    'Guia de interpretacion de fuentes',
                    'Debate en clase',
                    'Trabajo colaborativo',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Participacion critica y respeto por la palabra',
                    'Cumplimiento en actividades y consultas',
                ],
            },
        },
        'ciencias naturales': {
            'basica': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: ecosistemas y seres vivos',
                    'Parcial 2: materia y energia',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Taller de ciencias',
                    'Laboratorio guiado',
                    'Mapa conceptual',
                    'Quiz de seguimiento',
                    'Informe experimental',
                    'Guia de observacion',
                    'Trabajo colaborativo',
                    'Practica aplicada',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Participacion en laboratorio',
                    'Responsabilidad y cuidado del material',
                ],
            },
            'avanzada': {
                ActividadEvaluativa.DIMENSION_PARCIAL: [
                    'Parcial 1: celula y sistemas biologicos',
                    'Parcial 2: fuerzas, energia y transformaciones',
                ],
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                    'Taller de analisis cientifico',
                    'Laboratorio guiado',
                    'Mapa conceptual de procesos',
                    'Quiz de seguimiento',
                    'Informe experimental',
                    'Guia de aplicacion',
                    'Trabajo colaborativo',
                    'Practica de observacion',
                ],
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                    'Participacion y rigor en laboratorio',
                    'Responsabilidad y manejo del material',
                ],
            },
        },
    }

    grupo = 'basica' if es_basica else 'avanzada'
    if asignatura_normalizada in plantillas:
        return plantillas[asignatura_normalizada][grupo]

    return {
        ActividadEvaluativa.DIMENSION_PARCIAL: [
            'Parcial 1',
            'Parcial 2',
        ],
        ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
            'Actividad de seguimiento 1',
            'Actividad de seguimiento 2',
            'Actividad de seguimiento 3',
            'Actividad de seguimiento 4',
            'Actividad de seguimiento 5',
            'Actividad de seguimiento 6',
            'Actividad de seguimiento 7',
            'Actividad de seguimiento 8',
        ],
        ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
            'Participacion y disposicion',
            'Cumplimiento y responsabilidad',
        ],
    }


def asignar_nombres(actividades, plantillas_dimension):
    for index, actividad in enumerate(actividades, start=1):
        if index <= len(plantillas_dimension):
            actividad.nombre = plantillas_dimension[index - 1]
        else:
            actividad.nombre = f'{plantillas_dimension[-1]} {index}'


class Command(BaseCommand):
    help = 'Normaliza las actividades evaluativas del periodo para que cada dimension sume 100% interno.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--periodo-id',
            type=int,
            help='ID del periodo academico a normalizar. Si no se indica, se usa el periodo activo.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        periodo_id = options.get('periodo_id')
        if periodo_id:
            periodo = PeriodoAcademico.objects.select_related('anio_lectivo').filter(pk=periodo_id).first()
        else:
            periodo = PeriodoAcademico.objects.select_related('anio_lectivo').filter(activo=True).order_by('numero').first()

        if not periodo:
            raise CommandError('No se encontro un periodo academico para normalizar.')

        actividades = list(
            ActividadEvaluativa.objects.select_related(
                'carga_academica__asignatura',
                'carga_academica__grupo__grado',
            ).filter(periodo=periodo).order_by('carga_academica_id', 'fecha', 'id')
        )
        if not actividades:
            raise CommandError('No existen actividades registradas en el periodo seleccionado.')

        actividades_por_carga = {}
        for actividad in actividades:
            actividades_por_carga.setdefault(actividad.carga_academica_id, []).append(actividad)

        total_actualizadas = 0
        resumen = []

        for actividades_carga in actividades_por_carga.values():
            carga = actividades_carga[0].carga_academica
            grado = obtener_grado_numerico(carga)
            plantillas = obtener_plantillas(carga.asignatura.nombre, grado)

            ordenadas = sorted(actividades_carga, key=lambda item: (item.fecha, item.id))
            if len(ordenadas) < 5:
                raise CommandError(
                    f'La carga {carga} no tiene suficientes actividades para distribuir por dimensiones.'
                )

            actitudinales = ordenadas[:2]
            parciales = ordenadas[-2:]
            ids_reservados = {actividad.id for actividad in actitudinales + parciales}
            seguimiento = [actividad for actividad in ordenadas if actividad.id not in ids_reservados]

            grupos = {
                ActividadEvaluativa.DIMENSION_PARCIAL: parciales,
                ActividadEvaluativa.DIMENSION_ACTIVIDADES: seguimiento,
                ActividadEvaluativa.DIMENSION_ACTITUDINAL: actitudinales,
            }

            for dimension, items in grupos.items():
                porcentajes = repartir_porcentajes(len(items))
                asignar_nombres(items, plantillas[dimension])
                for actividad, porcentaje in zip(items, porcentajes):
                    actividad.dimension = dimension
                    actividad.porcentaje = porcentaje
                    actividad.activa = True
                    actividad.save(update_fields=['nombre', 'dimension', 'porcentaje', 'activa'])
                    total_actualizadas += 1

            resumen.append(
                f'{carga.asignatura.nombre} - {carga.grupo}: '
                f'{len(parciales)} parciales, {len(seguimiento)} actividades, {len(actitudinales)} actitudinales'
            )

        self.stdout.write(self.style.SUCCESS(
            f'Se normalizaron {total_actualizadas} actividades del {periodo.nombre} ({periodo.anio_lectivo.anio}).'
        ))
        for linea in resumen[:10]:
            self.stdout.write(f' - {linea}')
        if len(resumen) > 10:
            self.stdout.write(f' - ... y {len(resumen) - 10} carga(s) adicional(es).')
