from datetime import date, timedelta
from decimal import Decimal
from random import Random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import localdate

from academico.models import Estudiante, PeriodoAcademico
from alertas.utils import evaluar_alertas_academicas
from evaluacion.models import ActividadEvaluativa, Calificacion


class Command(BaseCommand):
    help = (
        "Reorganiza fechas y calificaciones del periodo activo para dejar informacion "
        "academica mas reciente y con mayor variacion analitica."
    )

    DIMENSION_BIAS = {
        ActividadEvaluativa.DIMENSION_PARCIAL: Decimal("-0.10"),
        ActividadEvaluativa.DIMENSION_ACTIVIDADES: Decimal("0.04"),
        ActividadEvaluativa.DIMENSION_ACTITUDINAL: Decimal("0.12"),
    }

    SUBJECT_BIAS = {
        "Matematicas": Decimal("-0.22"),
        "Lengua Castellana": Decimal("0.06"),
        "Ciencias Naturales": Decimal("-0.08"),
        "Ciencias Sociales": Decimal("0.14"),
        "Ingles": Decimal("-0.06"),
        "Tecnologia e Informatica": Decimal("0.08"),
        "Emprendimiento": Decimal("0.18"),
        "Base de Datos": Decimal("0.02"),
        "Programacion Python": Decimal("-0.02"),
    }

    PROFILE_BASES = {
        "critico": Decimal("2.20"),
        "riesgo": Decimal("2.80"),
        "basico": Decimal("3.35"),
        "alto": Decimal("4.15"),
        "sobresaliente": Decimal("4.65"),
    }

    PROFILE_WEIGHTS = (
        "critico",
        "riesgo",
        "riesgo",
        "basico",
        "basico",
        "basico",
        "basico",
        "alto",
        "alto",
        "sobresaliente",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fecha",
            type=str,
            help="Fecha limite en formato YYYY-MM-DD para reorganizar actividades y notas. Por defecto usa la fecha local.",
        )

    def handle(self, *args, **options):
        fecha_objetivo = self._resolver_fecha(options.get("fecha"))
        periodo = (
            PeriodoAcademico.objects.select_related("anio_lectivo")
            .filter(activo=True)
            .order_by("numero")
            .first()
        )
        if not periodo:
            raise CommandError("No hay un periodo academico activo.")

        actividades = list(
            ActividadEvaluativa.objects.select_related(
                "carga_academica",
                "carga_academica__grupo",
                "carga_academica__grupo__grado",
                "carga_academica__asignatura",
            ).filter(periodo=periodo, activa=True).order_by(
                "carga_academica_id",
                "fecha",
                "dimension",
                "id",
            )
        )
        if not actividades:
            raise CommandError("No hay actividades activas en el periodo actual.")

        fechas_objetivo = self._fechas_objetivo(periodo, fecha_objetivo)

        actividades_por_carga = {}
        for actividad in actividades:
            actividades_por_carga.setdefault(actividad.carga_academica_id, []).append(actividad)

        fechas_actualizadas = 0
        notas_actualizadas = 0
        estudiantes_recalculados = set()

        with transaction.atomic():
            for actividades_carga in actividades_por_carga.values():
                fechas_actualizadas += self._actualizar_fechas(periodo, actividades_carga, fechas_objetivo)
                notas_actualizadas += self._actualizar_notas(actividades_carga, estudiantes_recalculados)

            for estudiante_id in estudiantes_recalculados:
                estudiante = Estudiante.objects.get(pk=estudiante_id)
                evaluar_alertas_academicas(estudiante)

        self.stdout.write(self.style.SUCCESS("Periodo activo enriquecido correctamente."))
        self.stdout.write(f"Periodo: {periodo.nombre} ({periodo.anio_lectivo.anio})")
        self.stdout.write(f"Fecha limite de reorganizacion: {fecha_objetivo}")
        self.stdout.write(f"Fechas de actividades actualizadas: {fechas_actualizadas}")
        self.stdout.write(f"Calificaciones recalculadas: {notas_actualizadas}")
        self.stdout.write(f"Estudiantes revaluados para alertas: {len(estudiantes_recalculados)}")

    def _resolver_fecha(self, valor):
        if not valor:
            return localdate()
        try:
            return date.fromisoformat(valor)
        except ValueError as exc:
            raise CommandError("La fecha debe ir en formato YYYY-MM-DD.") from exc

    def _fechas_objetivo(self, periodo, fecha_objetivo):
        fecha_final = min(max(fecha_objetivo, periodo.fecha_inicio), periodo.fecha_fin)
        dias_habiles = []
        actual = periodo.fecha_inicio
        while actual <= fecha_final:
            if actual.weekday() < 5:
                dias_habiles.append(actual)
            actual += timedelta(days=1)
        if not dias_habiles:
            return [periodo.fecha_inicio]
        return dias_habiles

    def _actualizar_fechas(self, periodo, actividades_carga, fechas_objetivo):
        actualizadas = 0
        ordenadas = list(actividades_carga)
        fechas = list(fechas_objetivo[:len(ordenadas)])
        if len(fechas) < len(ordenadas):
            fechas.extend([fechas_objetivo[-1]] * (len(ordenadas) - len(fechas)))

        cambios = []
        for actividad, fecha in zip(ordenadas, fechas):
            fecha_objetivo = min(max(fecha, periodo.fecha_inicio), periodo.fecha_fin)
            if actividad.fecha != fecha_objetivo:
                actividad.fecha = fecha_objetivo
                actualizadas += 1
                cambios.append(actividad)
        if cambios:
            ActividadEvaluativa.objects.bulk_update(cambios, ["fecha"], batch_size=500)
        return actualizadas

    def _actualizar_notas(self, actividades_carga, estudiantes_recalculados):
        actualizadas = 0
        carga = actividades_carga[0].carga_academica
        estudiantes = list(
            Estudiante.objects.filter(grupo=carga.grupo, activo=True).order_by("apellidos", "nombres", "id")
        )
        actividades_ordenadas = sorted(actividades_carga, key=lambda item: (item.fecha, item.dimension, item.id))
        total_actividades = max(len(actividades_ordenadas), 1)
        actividad_ids = [actividad.id for actividad in actividades_ordenadas]
        estudiante_ids = [estudiante.id for estudiante in estudiantes]
        existentes = {
            (calificacion.actividad_id, calificacion.estudiante_id): calificacion
            for calificacion in Calificacion.objects.filter(
                actividad_id__in=actividad_ids,
                estudiante_id__in=estudiante_ids,
            )
        }
        cambios = []
        nuevos = []

        for posicion, estudiante in enumerate(estudiantes, start=1):
            perfil = self.PROFILE_WEIGHTS[(posicion - 1) % len(self.PROFILE_WEIGHTS)]
            base = self.PROFILE_BASES[perfil]
            tendencia = self._tendencia_estudiante(estudiante.id, carga.id)

            for indice, actividad in enumerate(actividades_ordenadas, start=1):
                nota = self._calcular_nota(
                    base=base,
                    perfil=perfil,
                    tendencia=tendencia,
                    actividad=actividad,
                    indice=indice,
                    total_actividades=total_actividades,
                    estudiante_id=estudiante.id,
                )

                observacion = self._observacion_nota(nota, perfil)
                calificacion = existentes.get((actividad.id, estudiante.id))
                if calificacion:
                    calificacion.nota = nota
                    calificacion.observacion = observacion
                    cambios.append(calificacion)
                else:
                    nuevos.append(Calificacion(
                        actividad=actividad,
                        estudiante=estudiante,
                        nota=nota,
                        observacion=observacion,
                    ))
                actualizadas += 1
                estudiantes_recalculados.add(estudiante.id)

        if nuevos:
            Calificacion.objects.bulk_create(nuevos, batch_size=1000)
        if cambios:
            Calificacion.objects.bulk_update(cambios, ["nota", "observacion"], batch_size=1000)
        return actualizadas

    def _tendencia_estudiante(self, estudiante_id, carga_id):
        rng = Random(f"trend-{estudiante_id}-{carga_id}")
        return Decimal(str(round(rng.uniform(-0.45, 0.45), 2)))

    def _calcular_nota(self, base, perfil, tendencia, actividad, indice, total_actividades, estudiante_id):
        rng = Random(f"nota-{actividad.id}-{estudiante_id}")
        subject_bias = self.SUBJECT_BIAS.get(actividad.carga_academica.asignatura.nombre, Decimal("0"))
        dimension_bias = self.DIMENSION_BIAS.get(actividad.dimension, Decimal("0"))
        progress = Decimal(str(round((indice - 1) / max(total_actividades - 1, 1), 2)))
        noise = Decimal(str(round(rng.uniform(-0.38, 0.38), 2)))

        if perfil == "critico":
            trend_component = tendencia * (progress - Decimal("0.10"))
        elif perfil == "riesgo":
            trend_component = tendencia * progress
        elif perfil == "basico":
            trend_component = tendencia * (progress + Decimal("0.10"))
        elif perfil == "alto":
            trend_component = tendencia * (progress + Decimal("0.18"))
        else:
            trend_component = tendencia * (progress + Decimal("0.24"))

        nota = base + subject_bias + dimension_bias + trend_component + noise
        nota = nota.quantize(Decimal("0.01"))
        return max(Decimal("1.50"), min(Decimal("5.00"), nota))

    def _observacion_nota(self, nota, perfil):
        if nota < Decimal("2.50"):
            return "Desempeno bajo. Requiere apoyo inmediato y plan de mejoramiento."
        if nota < Decimal("3.00"):
            return "Desempeno en riesgo. Se recomienda refuerzo y seguimiento."
        if nota < Decimal("4.00"):
            return "Desempeno basico. Mantener constancia en clase y entregas."
        if perfil in {"alto", "sobresaliente"} and nota >= Decimal("4.50"):
            return "Desempeno alto y sostenido. Evidencia dominio de la competencia."
        return "Desempeno adecuado de acuerdo con el seguimiento del periodo."
