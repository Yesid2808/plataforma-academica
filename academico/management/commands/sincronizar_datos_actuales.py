from datetime import date, timedelta
from decimal import Decimal
from random import Random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import localdate

from academico.models import CargaAcademica, Estudiante, HorarioClase, PeriodoAcademico
from alertas.utils import evaluar_alertas_academicas
from asistencia.models import Asistencia
from evaluacion.models import ActividadEvaluativa, Calificacion


class Command(BaseCommand):
    help = (
        "Sincroniza el periodo vigente y completa asistencia, actividades y "
        "calificaciones faltantes hasta la fecha indicada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fecha",
            type=str,
            help="Fecha objetivo en formato YYYY-MM-DD. Por defecto usa la fecha local del sistema.",
        )

    def handle(self, *args, **options):
        fecha_objetivo = self._resolver_fecha(options.get("fecha"))
        periodo = (
            PeriodoAcademico.objects.select_related("anio_lectivo")
            .filter(fecha_inicio__lte=fecha_objetivo, fecha_fin__gte=fecha_objetivo)
            .order_by("numero")
            .first()
        )
        if not periodo:
            raise CommandError(
                f"No existe un periodo academico configurado para la fecha {fecha_objetivo}."
            )

        cargas = list(
            CargaAcademica.objects.filter(
                activo=True,
                anio_lectivo=periodo.anio_lectivo,
            ).select_related(
                "grupo",
                "grupo__grado",
                "asignatura",
                "docente",
                "anio_lectivo",
            )
        )
        if not cargas:
            raise CommandError("No hay cargas academicas activas para el anio lectivo vigente.")

        dias_habiles = self._dias_habiles(periodo.fecha_inicio, fecha_objetivo)
        if not dias_habiles:
            raise CommandError("La fecha objetivo no tiene dias habiles acumulados dentro del periodo.")

        with transaction.atomic():
            periodos_actualizados = self._sincronizar_periodos_activos(periodo)
            actividades_actualizadas = self._garantizar_actividad_hasta_hoy(cargas, periodo, fecha_objetivo)
            asistencias_creadas = self._completar_asistencia(cargas, dias_habiles)
            calificaciones_creadas = self._completar_calificaciones(cargas, periodo, fecha_objetivo)
            alertas_recalculadas = self._recalcular_alertas(cargas)

        self.stdout.write(self.style.SUCCESS("Sincronizacion completada correctamente."))
        self.stdout.write(f"Fecha objetivo: {fecha_objetivo}")
        self.stdout.write(f"Periodo vigente: {periodo.nombre} ({periodo.fecha_inicio} a {periodo.fecha_fin})")
        self.stdout.write(f"Periodos con estado ajustado: {periodos_actualizados}")
        self.stdout.write(f"Actividades creadas o movidas hasta hoy: {actividades_actualizadas}")
        self.stdout.write(f"Asistencias creadas: {asistencias_creadas}")
        self.stdout.write(f"Calificaciones creadas: {calificaciones_creadas}")
        self.stdout.write(f"Estudiantes revaluados para alertas: {alertas_recalculadas}")

    def _resolver_fecha(self, valor):
        if not valor:
            return localdate()
        try:
            return date.fromisoformat(valor)
        except ValueError as exc:
            raise CommandError("La fecha debe ir en formato YYYY-MM-DD.") from exc

    def _dias_habiles(self, inicio, fin):
        dias = []
        actual = inicio
        while actual <= fin:
            if actual.weekday() < 5:
                dias.append(actual)
            actual += timedelta(days=1)
        return dias

    def _sincronizar_periodos_activos(self, periodo_actual):
        actualizados = 0
        periodos = PeriodoAcademico.objects.filter(anio_lectivo=periodo_actual.anio_lectivo)
        for periodo in periodos:
            debe_estar_activo = periodo.id == periodo_actual.id
            if periodo.activo != debe_estar_activo:
                periodo.activo = debe_estar_activo
                periodo.save(update_fields=["activo"])
                actualizados += 1
        return actualizados

    def _garantizar_actividad_hasta_hoy(self, cargas, periodo, fecha_objetivo):
        ajustadas = 0
        for carga in cargas:
            actividades_periodo = list(
                ActividadEvaluativa.objects.filter(
                    carga_academica=carga,
                    periodo=periodo,
                ).order_by("fecha", "id")
            )
            if any(actividad.fecha <= fecha_objetivo for actividad in actividades_periodo):
                continue

            futura = next((actividad for actividad in actividades_periodo if actividad.fecha > fecha_objetivo), None)
            if futura:
                futura.fecha = fecha_objetivo
                futura.save(update_fields=["fecha"])
                ajustadas += 1
                continue

            porcentaje_existente = sum(
                (actividad.porcentaje for actividad in actividades_periodo),
                Decimal("0"),
            )
            porcentaje_disponible = max(Decimal("0"), Decimal("100.00") - porcentaje_existente)
            if porcentaje_disponible <= Decimal("0"):
                continue

            porcentaje = min(Decimal("20.00"), porcentaje_disponible).quantize(Decimal("0.01"))
            ActividadEvaluativa.objects.create(
                carga_academica=carga,
                periodo=periodo,
                nombre=f"Seguimiento {fecha_objetivo:%d-%m}",
                dimension=ActividadEvaluativa.DIMENSION_ACTIVIDADES,
                porcentaje=porcentaje,
                fecha=fecha_objetivo,
                activa=True,
            )
            ajustadas += 1
        return ajustadas

    def _completar_asistencia(self, cargas, dias_habiles):
        creadas = 0
        for carga in cargas:
            dias_programados = set(
                HorarioClase.objects.filter(carga_academica=carga).values_list("dia_semana", flat=True).distinct()
            )
            estudiantes = list(
                Estudiante.objects.filter(grupo=carga.grupo, activo=True).order_by("id")
            )
            for dia in dias_habiles:
                if dias_programados and dia.isoweekday() not in dias_programados:
                    continue
                existentes = set(
                    Asistencia.objects.filter(carga_academica=carga, fecha=dia).values_list("estudiante_id", flat=True)
                )
                for estudiante in estudiantes:
                    if estudiante.id in existentes:
                        continue
                    estado = self._estado_asistencia(carga.id, estudiante.id, dia)
                    Asistencia.objects.create(
                        estudiante=estudiante,
                        carga_academica=carga,
                        fecha=dia,
                        estado=estado,
                        observacion="" if estado == "P" else "Sincronizacion automatica hasta la fecha actual.",
                    )
                    creadas += 1
        return creadas

    def _completar_calificaciones(self, cargas, periodo, fecha_objetivo):
        creadas = 0
        actividades = (
            ActividadEvaluativa.objects.filter(
                carga_academica__in=cargas,
                periodo=periodo,
                fecha__lte=fecha_objetivo,
                activa=True,
            )
            .select_related("carga_academica", "carga_academica__grupo", "carga_academica__asignatura")
            .order_by("fecha", "id")
        )
        for actividad in actividades:
            estudiantes = list(
                Estudiante.objects.filter(grupo=actividad.carga_academica.grupo, activo=True).order_by("id")
            )
            existentes = set(
                Calificacion.objects.filter(actividad=actividad).values_list("estudiante_id", flat=True)
            )
            for indice, estudiante in enumerate(estudiantes, start=1):
                if estudiante.id in existentes:
                    continue
                nota = self._nota_calculada(actividad, estudiante.id, indice)
                Calificacion.objects.create(
                    actividad=actividad,
                    estudiante=estudiante,
                    nota=nota,
                    observacion="Sincronizacion automatica" if nota < Decimal("3.00") else "",
                )
                creadas += 1
        return creadas

    def _recalcular_alertas(self, cargas):
        grupo_ids = {carga.grupo_id for carga in cargas}
        estudiantes = Estudiante.objects.filter(grupo_id__in=grupo_ids, activo=True).distinct()
        total = 0
        for estudiante in estudiantes:
            evaluar_alertas_academicas(estudiante)
            total += 1
        return total

    def _estado_asistencia(self, carga_id, estudiante_id, dia):
        randomizer = Random(f"{carga_id}-{estudiante_id}-{dia.isoformat()}")
        roll = randomizer.random()
        if roll < 0.07:
            return "A"
        if roll < 0.12:
            return "T"
        if roll < 0.16:
            return "J"
        return "P"

    def _nota_calculada(self, actividad, estudiante_id, indice):
        sesgo_asignatura = {
            "Matematicas": Decimal("-0.20"),
            "Lengua Castellana": Decimal("0.05"),
            "Ciencias Naturales": Decimal("-0.05"),
            "Ciencias Sociales": Decimal("0.10"),
            "Ingles": Decimal("-0.08"),
            "Tecnologia e Informatica": Decimal("0.06"),
            "Emprendimiento": Decimal("0.12"),
            "Base de Datos": Decimal("0.03"),
            "Programacion Python": Decimal("0.00"),
        }.get(actividad.carga_academica.asignatura.nombre, Decimal("0"))
        randomizer = Random(f"{actividad.id}-{estudiante_id}-{indice}")
        if indice <= 5:
            base = Decimal(str(round(randomizer.uniform(1.9, 2.9), 2)))
        elif indice <= 12:
            base = Decimal(str(round(randomizer.uniform(2.8, 3.6), 2)))
        elif indice <= 24:
            base = Decimal(str(round(randomizer.uniform(3.4, 4.3), 2)))
        else:
            base = Decimal(str(round(randomizer.uniform(4.0, 4.8), 2)))
        ajuste_periodo = Decimal(str(round(actividad.periodo.numero * 0.04, 2)))
        nota = (base + sesgo_asignatura + ajuste_periodo).quantize(Decimal("0.01"))
        return max(Decimal("1.50"), min(Decimal("5.00"), nota))
