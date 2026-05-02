from datetime import date, timedelta
from decimal import Decimal
from random import Random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from academico.utils import inferir_genero_por_nombre
from academico.models import (
    AnioLectivo,
    Asignatura,
    CargaAcademica,
    Estudiante,
    Grado,
    Grupo,
    PeriodoAcademico,
)
from alertas.utils import (
    asegurar_configuraciones_alertas_academicas,
    asegurar_configuraciones_inasistencia,
    evaluar_alertas_academicas,
)
from alertas.models import AlertaTemprana, SeguimientoAlerta
from asistencia.models import Asistencia
from evaluacion.models import ActividadEvaluativa, Calificacion


class Command(BaseCommand):
    help = "Crea datos demo realistas para grados 8-B y 9-A con materias base."

    FIRST_NAMES = [
        "Santiago", "Mateo", "Samuel", "David", "Daniel", "Nicolas", "Juan", "Miguel",
        "Andres", "Sebastian", "Valentina", "Isabella", "Sofia", "Camila", "Mariana",
        "Gabriela", "Laura", "Salome", "Luciana", "Daniela", "Alejandro", "Carlos",
        "Maria", "Ana", "Juliana", "Emiliano", "Manuela", "Sara", "Luisa", "Tomas",
    ]
    LAST_NAMES = [
        "Garcia", "Martinez", "Rodriguez", "Lopez", "Hernandez", "Perez", "Gomez",
        "Torres", "Ramirez", "Castro", "Mejia", "Rojas", "Moreno", "Suarez", "Vargas",
        "Mendoza", "Ortega", "Herrera", "Jimenez", "Carmona", "Barrios", "Padilla",
        "Correa", "Acosta", "Navarro", "Pacheco", "Ibarra", "Florez", "Quintero", "Molina",
    ]
    SUBJECTS = [
        ("Matematicas", 5),
        ("Lengua Castellana", 4),
        ("Ciencias Naturales", 4),
        ("Ciencias Sociales", 3),
        ("Ingles", 3),
    ]
    TARGET_GROUPS = [
        ("8", "B", 13, 15),
        ("9", "A", 15, 17),
    ]

    def handle(self, *args, **options):
        self.random = Random(20260410)

        with transaction.atomic():
            anio = self.ensure_academic_year()
            docentes = self.ensure_teachers()
            asignaturas = self.ensure_subjects()
            grupos = self.ensure_groups()
            estudiantes = self.ensure_students(grupos)
            cargas = self.ensure_cargas(anio, grupos, asignaturas, docentes)
            actividades = self.ensure_activities(anio, cargas)
            self.ensure_grades(actividades)
            self.ensure_attendance(cargas)
            self.ensure_alert_config()
            self.ensure_alerts(estudiantes)
            self.ensure_alert_followups(docentes)

        self.stdout.write(self.style.SUCCESS("Datos demo creados/actualizados correctamente."))
        for grupo in grupos:
            self.stdout.write(f"{grupo}: {grupo.estudiantes.filter(activo=True).count()} estudiantes activos")

    def ensure_academic_year(self):
        anio, _ = AnioLectivo.objects.get_or_create(anio=2026, defaults={"activo": True})

        periodos = [
            ("Primer periodo", 1, date(2026, 1, 27), date(2026, 4, 10)),
            ("Segundo periodo", 2, date(2026, 4, 13), date(2026, 6, 19)),
            ("Tercer periodo", 3, date(2026, 7, 7), date(2026, 9, 11)),
            ("Cuarto periodo", 4, date(2026, 9, 14), date(2026, 11, 27)),
        ]
        for nombre, numero, inicio, fin in periodos:
            PeriodoAcademico.objects.get_or_create(
                anio_lectivo=anio,
                numero=numero,
                defaults={
                    "nombre": nombre,
                    "fecha_inicio": inicio,
                    "fecha_fin": fin,
                    "activo": numero == 1,
                },
            )
        return anio

    def ensure_teachers(self):
        User = get_user_model()
        teachers = []
        teacher_data = [
            ("doc_matematicas", "Adriana", "Fuentes"),
            ("doc_lengua", "Ricardo", "Benitez"),
            ("doc_ciencias", "Patricia", "Molina"),
            ("doc_sociales", "Jorge", "Caballero"),
            ("doc_ingles", "Claudia", "Sarmiento"),
        ]

        for username, first_name, last_name in teacher_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{username}@colegio.edu.co",
                    "rol": "DOC",
                    "is_staff": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password("Docente2026*")
                user.save()
            teachers.append(user)
        return teachers

    def ensure_subjects(self):
        subjects = []
        for name, intensity in self.SUBJECTS:
            subject, _ = Asignatura.objects.get_or_create(
                nombre=name,
                defaults={"intensidad_horaria": intensity, "activa": True},
            )
            subjects.append(subject)
        return subjects

    def ensure_groups(self):
        grupos = []
        for grado_nombre, grupo_nombre, _, _ in self.TARGET_GROUPS:
            grado, _ = Grado.objects.get_or_create(nombre=grado_nombre)
            grupo, _ = Grupo.objects.get_or_create(
                grado=grado,
                nombre=grupo_nombre,
                defaults={"activo": True},
            )
            grupos.append(grupo)
        return grupos

    def ensure_students(self, grupos):
        all_students = []
        for index, grupo in enumerate(grupos):
            _, _, edad_min, edad_max = self.TARGET_GROUPS[index]
            existing_count = grupo.estudiantes.filter(activo=True).count()
            needed = max(0, 30 - existing_count)

            for number in range(existing_count + 1, existing_count + needed + 1):
                name = self.FIRST_NAMES[(number + index * 7) % len(self.FIRST_NAMES)]
                second_name = self.FIRST_NAMES[(number + index * 11 + 3) % len(self.FIRST_NAMES)]
                last_name = self.LAST_NAMES[(number + index * 5) % len(self.LAST_NAMES)]
                second_last_name = self.LAST_NAMES[(number + index * 9 + 4) % len(self.LAST_NAMES)]
                documento = f"{grupo.grado.nombre}{grupo.nombre}{number:02d}2026".replace(" ", "")
                birth_year = 2026 - self.random.randint(edad_min, edad_max)
                birth_date = date(birth_year, self.random.randint(1, 12), self.random.randint(1, 28))

                student, _ = Estudiante.objects.get_or_create(
                    documento=documento,
                    defaults={
                        "tipo_documento": "TI",
                        "nombres": f"{name} {second_name}",
                        "apellidos": f"{last_name} {second_last_name}",
                        "genero": inferir_genero_por_nombre(name),
                        "fecha_nacimiento": birth_date,
                        "grupo": grupo,
                        "correo": f"{name.lower()}.{last_name.lower()}{number}@estudiante.edu.co",
                        "whatsapp": f"300{self.random.randint(1000000, 9999999)}",
                        "acudiente": f"{self.FIRST_NAMES[(number + 2) % len(self.FIRST_NAMES)]} {last_name}",
                        "correo_acudiente": f"acudiente.{last_name.lower()}{number}@email.com",
                        "telefono_acudiente": f"301{self.random.randint(1000000, 9999999)}",
                        "whatsapp_acudiente": f"301{self.random.randint(1000000, 9999999)}",
                        "direccion": f"Calle {self.random.randint(10, 95)} # {self.random.randint(1, 80)}-{self.random.randint(1, 90)}, Atlantico",
                        "activo": True,
                    },
                )
                all_students.append(student)

            all_students.extend(grupo.estudiantes.filter(activo=True))
        return list(set(all_students))

    def ensure_cargas(self, anio, grupos, asignaturas, docentes):
        cargas = []
        for grupo in grupos:
            for index, asignatura in enumerate(asignaturas):
                carga, _ = CargaAcademica.objects.get_or_create(
                    docente=docentes[index],
                    grupo=grupo,
                    asignatura=asignatura,
                    anio_lectivo=anio,
                    defaults={"activo": True},
                )
                cargas.append(carga)
        return cargas

    def ensure_activities(self, anio, cargas):
        periodo = PeriodoAcademico.objects.get(anio_lectivo=anio, numero=1)
        actividades = []
        activity_data = [
            ("Quiz diagnostico", Decimal("20.00"), date(2026, 2, 14)),
            ("Taller aplicado", Decimal("30.00"), date(2026, 3, 6)),
            ("Evaluacion de periodo", Decimal("50.00"), date(2026, 4, 3)),
        ]

        for carga in cargas:
            for nombre, porcentaje, fecha in activity_data:
                actividad, _ = ActividadEvaluativa.objects.get_or_create(
                    carga_academica=carga,
                    periodo=periodo,
                    nombre=nombre,
                    defaults={
                        "porcentaje": porcentaje,
                        "fecha": fecha,
                        "activa": True,
                    },
                )
                actividades.append(actividad)
        return actividades

    def ensure_grades(self, actividades):
        for actividad in actividades:
            students = Estudiante.objects.filter(
                grupo=actividad.carga_academica.grupo,
                activo=True
            ).order_by('apellidos', 'nombres')
            subject_bias = {
                "Matematicas": -0.25,
                "Lengua Castellana": 0.10,
                "Ciencias Naturales": -0.05,
                "Ciencias Sociales": 0.15,
                "Ingles": -0.10,
            }.get(actividad.carga_academica.asignatura.nombre, 0)

            for position, student in enumerate(students, start=1):
                if position <= 4:
                    # Casos intencionales de bajo rendimiento para alimentar alertas y Power BI.
                    base_score = self.random.uniform(2.0, 2.8)
                elif position <= 8:
                    base_score = self.random.uniform(2.8, 3.4)
                else:
                    base_score = self.random.uniform(3.1, 4.8)

                base = Decimal(str(round(base_score + subject_bias, 2)))
                nota = max(Decimal("1.80"), min(Decimal("5.00"), base)).quantize(Decimal("0.01"))
                Calificacion.objects.update_or_create(
                    actividad=actividad,
                    estudiante=student,
                    defaults={
                        "nota": nota,
                        "observacion": "Requiere acompanamiento" if nota < Decimal("3.00") else "",
                    },
                )

    def ensure_attendance(self, cargas):
        start = date(2026, 3, 16)
        class_days = []
        current = start
        while len(class_days) < 12:
            if current.weekday() < 5:
                class_days.append(current)
            current += timedelta(days=1)

        for carga in cargas:
            students = Estudiante.objects.filter(grupo=carga.grupo, activo=True)
            for day in class_days:
                for student in students:
                    roll = self.random.random()
                    if roll < 0.08:
                        estado = "A"
                    elif roll < 0.14:
                        estado = "T"
                    elif roll < 0.17:
                        estado = "J"
                    else:
                        estado = "P"
                    Asistencia.objects.update_or_create(
                        estudiante=student,
                        carga_academica=carga,
                        fecha=day,
                        defaults={
                            "estado": estado,
                            "observacion": "Registro demo institucional" if estado != "P" else "",
                        },
                    )

    def ensure_alert_config(self):
        asegurar_configuraciones_inasistencia()
        asegurar_configuraciones_alertas_academicas()

    def ensure_alerts(self, students):
        for student in students:
            evaluar_alertas_academicas(student)

    def ensure_alert_followups(self, docentes):
        acciones = [
            ("CONTACTO_ACUDIENTE", "Se contacto al acudiente y se socializo el plan de acompanamiento."),
            ("APOYO_PEDAGOGICO", "Se asignaron actividades de refuerzo y revision semanal de avances."),
            ("COMPROMISO_ACADEMICO", "El estudiante firmo compromiso academico con seguimiento del director de grupo."),
            ("REMISION_ORIENTACION", "Caso remitido a orientacion escolar para valorar factores asociados al rendimiento."),
        ]
        resultados = ["EN_PROCESO", "PENDIENTE", "MEJORA", "SIN_MEJORA"]
        alertas = AlertaTemprana.objects.select_related("estudiante").filter(estado="ACTIVA").order_by("-nivel")[:18]

        for index, alerta in enumerate(alertas):
            accion, descripcion = acciones[index % len(acciones)]
            if SeguimientoAlerta.objects.filter(alerta=alerta, accion=accion).exists():
                continue

            SeguimientoAlerta.objects.create(
                alerta=alerta,
                registrado_por=docentes[index % len(docentes)] if docentes else None,
                accion=accion,
                descripcion=descripcion,
                resultado=resultados[index % len(resultados)],
                proxima_revision=date(2026, 4, 20) + timedelta(days=index % 10),
            )
