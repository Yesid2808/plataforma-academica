from django.core.management.base import BaseCommand
from django.db import transaction

from academico.models import Asignatura, CargaAcademica, Estudiante, Grado, Grupo, HorarioClase
from alertas.models import AlertaTemprana
from asistencia.models import Asistencia
from evaluacion.models import ActividadEvaluativa, Calificacion


class Command(BaseCommand):
    help = (
        "Depura la estructura curricular dejando solo las materias base y "
        "eliminando los grupos 10A, 10B, 11A y 11B con todas sus dependencias."
    )

    MATERIAS_PERMITIDAS = {
        "Ingles",
        "Matematicas",
        "Lengua Castellana",
        "Ciencias Sociales",
        "Ciencias Naturales",
    }
    GRADOS_ELIMINAR = {"10", "11"}

    def handle(self, *args, **options):
        grupos_eliminar = Grupo.objects.filter(grado__nombre__in=self.GRADOS_ELIMINAR)
        materias_eliminar = Asignatura.objects.exclude(nombre__in=self.MATERIAS_PERMITIDAS)
        cargas_grupos = CargaAcademica.objects.filter(grupo__in=grupos_eliminar)
        cargas_materias = CargaAcademica.objects.filter(asignatura__in=materias_eliminar)

        resumen_prev = {
            "grupos_eliminar": grupos_eliminar.count(),
            "grados_eliminar": Grado.objects.filter(nombre__in=self.GRADOS_ELIMINAR).count(),
            "materias_eliminar": materias_eliminar.count(),
            "estudiantes_grupos": Estudiante.objects.filter(grupo__in=grupos_eliminar).count(),
            "cargas_grupos": cargas_grupos.count(),
            "cargas_materias": cargas_materias.count(),
            "horarios_grupos": HorarioClase.objects.filter(carga_academica__in=cargas_grupos).count(),
            "horarios_materias": HorarioClase.objects.filter(carga_academica__in=cargas_materias).count(),
            "asistencias_grupos": Asistencia.objects.filter(carga_academica__in=cargas_grupos).count(),
            "asistencias_materias": Asistencia.objects.filter(carga_academica__in=cargas_materias).count(),
            "actividades_grupos": ActividadEvaluativa.objects.filter(carga_academica__in=cargas_grupos).count(),
            "actividades_materias": ActividadEvaluativa.objects.filter(carga_academica__in=cargas_materias).count(),
            "calificaciones_grupos": Calificacion.objects.filter(
                actividad__carga_academica__in=cargas_grupos
            ).count(),
            "calificaciones_materias": Calificacion.objects.filter(
                actividad__carga_academica__in=cargas_materias
            ).count(),
            "alertas_grupos": AlertaTemprana.objects.filter(estudiante__grupo__in=grupos_eliminar).count(),
        }

        with transaction.atomic():
            estudiantes_eliminados, _ = Estudiante.objects.filter(grupo__in=grupos_eliminar).delete()
            grupos_borrados, _ = grupos_eliminar.delete()
            grados_borrados, _ = Grado.objects.filter(nombre__in=self.GRADOS_ELIMINAR).delete()
            materias_borradas, _ = materias_eliminar.delete()

        materias_finales = list(Asignatura.objects.order_by("nombre").values_list("nombre", flat=True))
        grados_finales = list(Grado.objects.order_by("nombre").values_list("nombre", flat=True))
        grupos_finales = list(
            Grupo.objects.select_related("grado").order_by("grado__nombre", "nombre").values_list(
                "grado__nombre", "nombre"
            )
        )

        self.stdout.write(self.style.SUCCESS("Depuracion curricular completada correctamente."))
        for clave, valor in resumen_prev.items():
            self.stdout.write(f"{clave}: {valor}")
        self.stdout.write(f"estudiantes_eliminados: {estudiantes_eliminados}")
        self.stdout.write(f"grupos_borrados: {grupos_borrados}")
        self.stdout.write(f"grados_borrados: {grados_borrados}")
        self.stdout.write(f"materias_borradas: {materias_borradas}")
        self.stdout.write(f"materias_finales: {materias_finales}")
        self.stdout.write(f"grados_finales: {grados_finales}")
        self.stdout.write(f"grupos_finales: {grupos_finales}")
