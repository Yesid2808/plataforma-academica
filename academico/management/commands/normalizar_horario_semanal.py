from collections import Counter, defaultdict
from datetime import time
from random import Random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from academico.models import AnioLectivo, CargaAcademica, HorarioClase


class Command(BaseCommand):
    help = "Reconstruye un horario semanal completo de lunes a viernes para los grupos activos sin cruces."

    MORNING_ROWS = [
        (1, time(6, 30), time(7, 20)),
        (1, time(7, 20), time(8, 10)),
        (1, time(8, 25), time(9, 15)),
        (1, time(9, 15), time(10, 5)),
        (1, time(10, 20), time(11, 10)),
        (2, time(6, 30), time(7, 20)),
        (2, time(7, 20), time(8, 10)),
        (2, time(8, 25), time(9, 15)),
        (2, time(9, 15), time(10, 5)),
        (2, time(10, 20), time(11, 10)),
        (3, time(6, 30), time(7, 20)),
        (3, time(7, 20), time(8, 10)),
        (3, time(8, 25), time(9, 15)),
        (3, time(9, 15), time(10, 5)),
        (3, time(10, 20), time(11, 10)),
        (4, time(6, 30), time(7, 20)),
        (4, time(7, 20), time(8, 10)),
        (4, time(8, 25), time(9, 15)),
        (4, time(9, 15), time(10, 5)),
        (4, time(10, 20), time(11, 10)),
        (5, time(6, 30), time(7, 20)),
        (5, time(7, 20), time(8, 10)),
        (5, time(8, 25), time(9, 15)),
        (5, time(9, 15), time(10, 5)),
        (5, time(10, 20), time(11, 10)),
    ]

    AFTERNOON_ROWS = [
        (1, time(12, 30), time(13, 20)),
        (1, time(13, 20), time(14, 10)),
        (1, time(14, 25), time(15, 15)),
        (1, time(15, 15), time(16, 5)),
        (1, time(16, 20), time(17, 10)),
        (2, time(12, 30), time(13, 20)),
        (2, time(13, 20), time(14, 10)),
        (2, time(14, 25), time(15, 15)),
        (2, time(15, 15), time(16, 5)),
        (2, time(16, 20), time(17, 10)),
        (3, time(12, 30), time(13, 20)),
        (3, time(13, 20), time(14, 10)),
        (3, time(14, 25), time(15, 15)),
        (3, time(15, 15), time(16, 5)),
        (3, time(16, 20), time(17, 10)),
        (4, time(12, 30), time(13, 20)),
        (4, time(13, 20), time(14, 10)),
        (4, time(14, 25), time(15, 15)),
        (4, time(15, 15), time(16, 5)),
        (4, time(16, 20), time(17, 10)),
        (5, time(12, 30), time(13, 20)),
        (5, time(13, 20), time(14, 10)),
        (5, time(14, 25), time(15, 15)),
        (5, time(15, 15), time(16, 5)),
        (5, time(16, 20), time(17, 10)),
    ]

    SUBJECT_AULAS = {
        "Matematicas": ["Salon 201", "Salon 204", "Salon 205"],
        "Lengua Castellana": ["Salon 202", "Salon 206", "Salon 207"],
        "Ciencias Naturales": ["Lab Ciencias 1", "Lab Ciencias 2", "Lab Ciencias 3"],
        "Ciencias Sociales": ["Salon 203", "Salon 208", "Salon 209"],
        "Ingles": ["Language Room 1", "Language Room 2", "Language Room 3"],
        "Tecnologia e Informatica": ["Sala TIC 1", "Sala TIC 4", "Sala TIC 5"],
        "Emprendimiento": ["Aula Multiproposito 1", "Aula Multiproposito 2"],
        "Base de Datos": ["Sala TIC 2", "Sala TIC 6", "Sala TIC 7"],
        "Programacion Python": ["Sala TIC 3", "Sala TIC 8", "Sala TIC 9"],
    }

    TEACHER_AULAS = {
        "doc_matematicas": "Salon 201",
        "doc_matematicas_apoyo": "Salon 204",
        "doc_matematicas_3": "Salon 205",
        "doc_lengua": "Salon 202",
        "doc_lengua_apoyo": "Salon 206",
        "doc_lengua_3": "Salon 207",
        "doc_ciencias": "Lab Ciencias 1",
        "doc_ciencias_apoyo": "Lab Ciencias 2",
        "doc_ciencias_3": "Lab Ciencias 3",
        "doc_sociales": "Salon 203",
        "doc_sociales_apoyo": "Salon 208",
        "doc_sociales_3": "Salon 209",
        "doc_ingles": "Language Room 1",
        "doc_ingles_apoyo": "Language Room 2",
        "doc_ingles_3": "Language Room 3",
        "doc_tecnologia": "Sala TIC 1",
        "doc_tecnologia_2": "Sala TIC 4",
        "doc_tecnologia_3": "Sala TIC 5",
        "doc_emprendimiento": "Aula Multiproposito 1",
        "doc_emprendimiento_2": "Aula Multiproposito 2",
        "doc_bdatos": "Sala TIC 2",
        "doc_bdatos_2": "Sala TIC 6",
        "doc_bdatos_3": "Sala TIC 7",
        "doc_python": "Sala TIC 3",
        "doc_python_2": "Sala TIC 8",
        "doc_python_3": "Sala TIC 9",
    }

    @transaction.atomic
    def handle(self, *args, **options):
        anio = AnioLectivo.objects.filter(activo=True).order_by("-anio").first()
        if not anio:
            raise CommandError("No hay un ano lectivo activo.")

        cargas = list(
            CargaAcademica.objects.select_related(
                "docente",
                "grupo",
                "grupo__grado",
                "asignatura",
            ).filter(
                anio_lectivo=anio,
                activo=True,
            )
        )
        if not cargas:
            raise CommandError("No se encontraron cargas academicas activas para los grados configurados.")

        cargas_por_grupo = self._mapear_cargas_por_grupo(cargas)
        morning_groups, afternoon_groups = self._clasificar_grupos_activos(cargas_por_grupo)
        HorarioClase.objects.filter(carga_academica_id__in=[carga.id for carga in cargas]).delete()

        created = 0
        if morning_groups:
            created += self._persistir_shift(morning_groups, self.MORNING_ROWS, cargas_por_grupo)
        if afternoon_groups:
            created += self._persistir_shift(afternoon_groups, self.AFTERNOON_ROWS, cargas_por_grupo)

        self.stdout.write(self.style.SUCCESS("Horario semanal normalizado correctamente."))
        self.stdout.write(f"Bloques creados: {created}")

    def _mapear_cargas_por_grupo(self, cargas):
        cargas_por_grupo = {}
        for carga in cargas:
            key = (carga.grupo.grado.nombre, carga.grupo.nombre)
            cargas_por_grupo.setdefault(key, {})[carga.asignatura.nombre] = carga
        return cargas_por_grupo

    def _clasificar_grupos_activos(self, cargas_por_grupo):
        grupos = sorted(
            cargas_por_grupo.keys(),
            key=lambda item: (int(item[0]), item[1]),
        )
        morning_groups = [grupo for grupo in grupos if int(grupo[0]) <= 8]
        afternoon_groups = [grupo for grupo in grupos if int(grupo[0]) >= 9]
        return morning_groups, afternoon_groups

    def _persistir_shift(self, group_keys, rows, cargas_por_grupo):
        for key in group_keys:
            if key not in cargas_por_grupo:
                raise CommandError(f"Falta la estructura academica del grupo {key[0]}-{key[1]}.")

        cargas_shift = {key: cargas_por_grupo[key] for key in group_keys}
        rows_by_day = self._rows_by_day(rows)
        resolved_schedule = None

        for attempt in range(30):
            planes_por_grupo = {}
            for offset, key in enumerate(group_keys):
                planes_por_grupo[key] = self._planificar_grupo_por_dia(
                    cargas_shift[key],
                    len(rows_by_day),
                    offset + attempt,
                )

            candidate_schedule = {}
            try:
                for day, day_rows in rows_by_day.items():
                    plan_dia = {
                        key: list(planes_por_grupo[key][day])
                        for key in group_keys
                    }
                    candidate_schedule[day] = self._resolver_dia(day_rows, group_keys, plan_dia, cargas_shift)
            except CommandError:
                continue

            resolved_schedule = candidate_schedule
            break

        if resolved_schedule is None:
            raise CommandError("No fue posible construir el horario semanal del turno sin cruces.")

        created = 0
        for day, day_rows in rows_by_day.items():
            for row_data, row_assignment in zip(day_rows, resolved_schedule[day]):
                dia_semana, hora_inicio, hora_fin = row_data
                for group_key, subject_name in row_assignment.items():
                    if not subject_name:
                        continue
                    carga = cargas_shift[group_key][subject_name]
                    HorarioClase.objects.create(
                        carga_academica=carga,
                        dia_semana=dia_semana,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        aula=self._aula_para(carga),
                    )
                    created += 1
        return created

    def _rows_by_day(self, rows):
        rows_by_day = defaultdict(list)
        for row in rows:
            rows_by_day[row[0]].append(row)
        return dict(rows_by_day)

    def _planificar_grupo_por_dia(self, cargas_grupo, total_dias, offset):
        base_counts = Counter({
            subject: carga.asignatura.intensidad_horaria
            for subject, carga in cargas_grupo.items()
        })
        total_bloques = sum(base_counts.values())
        targets = self._daily_targets(total_bloques, total_dias, offset)

        for intento in range(80):
            rng = Random(20260429 + (offset * 101) + intento)
            remaining = base_counts.copy()
            plan = {day: [] for day in range(1, total_dias + 1)}
            asignaturas = sorted(
                remaining.keys(),
                key=lambda subject: (-remaining[subject], subject),
            )

            valido = True
            for subject_name in asignaturas:
                for _ in range(remaining[subject_name]):
                    candidate_days = [
                        day for day in range(1, total_dias + 1)
                        if len(plan[day]) < targets[day - 1] and plan[day].count(subject_name) < 2
                    ]
                    if not candidate_days:
                        valido = False
                        break

                    candidate_days.sort(
                        key=lambda day: (
                            len(plan[day]),
                            plan[day].count(subject_name),
                            rng.random(),
                        )
                    )
                    selected_day = candidate_days[0]
                    plan[selected_day].append(subject_name)

                if not valido:
                    break

            if not valido:
                continue

            if any(len(plan[day]) != targets[day - 1] for day in range(1, total_dias + 1)):
                continue

            return plan

        raise CommandError("No fue posible distribuir las materias por dia para un grupo.")

    def _daily_targets(self, total_bloques, total_dias, offset):
        base = total_bloques // total_dias
        remainder = total_bloques % total_dias
        targets = [base for _ in range(total_dias)]
        for index in range(remainder):
            targets[(offset + index) % total_dias] += 1
        return targets

    def _resolver_dia(self, day_rows, group_keys, plan_dia, cargas_shift):
        edges = []
        for group_key in group_keys:
            for subject_name in plan_dia[group_key]:
                edges.append({
                    "group": group_key,
                    "subject": subject_name,
                    "teacher": cargas_shift[group_key][subject_name].docente_id,
                })

        color_count = len(day_rows)
        group_colors = defaultdict(set)
        teacher_colors = defaultdict(set)
        edge_colors = {}

        def backtrack():
            if len(edge_colors) == len(edges):
                return True

            candidate_index = None
            candidate_colors = None
            for index, edge in enumerate(edges):
                if index in edge_colors:
                    continue
                available = [
                    color
                    for color in range(color_count)
                    if color not in group_colors[edge["group"]]
                    and color not in teacher_colors[edge["teacher"]]
                ]
                if candidate_colors is None or len(available) < len(candidate_colors):
                    candidate_index = index
                    candidate_colors = available
                if candidate_colors == []:
                    break

            if not candidate_colors:
                return False

            for color in candidate_colors:
                edge = edges[candidate_index]
                edge_colors[candidate_index] = color
                group_colors[edge["group"]].add(color)
                teacher_colors[edge["teacher"]].add(color)

                if backtrack():
                    return True

                del edge_colors[candidate_index]
                group_colors[edge["group"]].remove(color)
                teacher_colors[edge["teacher"]].remove(color)

            return False

        if not backtrack():
            raise CommandError("No fue posible construir un dia de horario sin cruces.")

        row_assignments = [{group_key: None for group_key in group_keys} for _ in range(color_count)]
        for index, color in edge_colors.items():
            edge = edges[index]
            row_assignments[color][edge["group"]] = edge["subject"]
        return row_assignments

    def _aula_para(self, carga):
        return self.TEACHER_AULAS.get(
            carga.docente.username,
            self.SUBJECT_AULAS.get(carga.asignatura.nombre, ["Salon general"])[0],
        )
