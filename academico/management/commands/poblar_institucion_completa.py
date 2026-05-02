from datetime import date, timedelta
from decimal import Decimal
from random import Random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from academico.models import (
    AnioLectivo,
    Asignatura,
    CargaAcademica,
    Estudiante,
    Grado,
    Grupo,
    PeriodoAcademico,
)
from academico.utils import inferir_genero_por_nombre
from alertas.utils import (
    asegurar_configuraciones_alertas_academicas,
    asegurar_configuraciones_inasistencia,
)
from asistencia.models import Asistencia
from evaluacion.management.commands.normalizar_actividades_periodo import (
    obtener_plantillas,
    repartir_porcentajes,
)
from evaluacion.models import ActividadEvaluativa, Calificacion


class Command(BaseCommand):
    help = (
        "Puebla la institucion completa de 6A a 11B con 30 estudiantes por salon, "
        "materias, docentes, actividades y calificaciones."
    )

    DOCENTES = [
        ("doc_matematicas", "Adriana", "Fuentes", "3004001001"),
        ("doc_matematicas_apoyo", "Felipe", "Barraza", "3004001006"),
        ("doc_matematicas_3", "Natalia", "Rosales", "3004001017"),
        ("doc_lengua", "Ricardo", "Benitez", "3004001002"),
        ("doc_lengua_apoyo", "Monica", "Villalba", "3004001013"),
        ("doc_lengua_3", "Yolanda", "Severiche", "3004001018"),
        ("doc_ciencias", "Patricia", "Molina", "3004001003"),
        ("doc_ciencias_apoyo", "Sergio", "Alvarez", "3004001014"),
        ("doc_ciencias_3", "Mauricio", "Polo", "3004001019"),
        ("doc_sociales", "Jorge", "Caballero", "3004001004"),
        ("doc_sociales_apoyo", "Karina", "Acosta", "3004001015"),
        ("doc_sociales_3", "Lina", "Escorcia", "3004001020"),
        ("doc_ingles", "Claudia", "Sarmiento", "3004001005"),
        ("doc_ingles_apoyo", "Diana", "Cuello", "3004001016"),
        ("doc_ingles_3", "Heidy", "Contreras", "3004001021"),
        ("doc_tecnologia", "Andres", "Caceres", "3004001007"),
        ("doc_tecnologia_2", "Camilo", "Sotelo", "3004001022"),
        ("doc_tecnologia_3", "Luz", "Mendoza", "3004001025"),
        ("doc_emprendimiento", "Laura", "Paternina", "3004001008"),
        ("doc_emprendimiento_2", "Mabel", "Lobo", "3004001026"),
        ("doc_bdatos", "Felipe", "Barrios", "3004001009"),
        ("doc_bdatos_2", "Sandra", "Ariza", "3004001023"),
        ("doc_bdatos_3", "Ruben", "Ortiz", "3004001027"),
        ("doc_python", "Valentina", "Mercado", "3004001010"),
        ("doc_python_2", "Julian", "Bustos", "3004001024"),
        ("doc_python_3", "Tatiana", "Marulanda", "3004001028"),
    ]

    MALE_NAMES = [
        "Santiago", "Mateo", "Samuel", "David", "Daniel", "Nicolas", "Juan", "Miguel",
        "Andres", "Sebastian", "Alejandro", "Carlos", "Emiliano", "Tomas", "Martin",
        "Angel", "Jose", "Kevin", "Esteban", "Jhon", "Cristian", "Luis", "Joaquin", "Thiago",
    ]
    FEMALE_NAMES = [
        "Valentina", "Isabella", "Sofia", "Camila", "Mariana", "Gabriela", "Laura", "Salome",
        "Luciana", "Daniela", "Maria", "Ana", "Juliana", "Manuela", "Sara", "Luisa",
        "Antonella", "Valeria", "Natalia", "Paula", "Alejandra", "Karol", "Melany", "Tatiana",
    ]
    LAST_NAMES = [
        "Garcia", "Martinez", "Rodriguez", "Lopez", "Hernandez", "Perez", "Gomez", "Torres",
        "Ramirez", "Castro", "Mejia", "Rojas", "Moreno", "Suarez", "Vargas", "Mendoza",
        "Ortega", "Herrera", "Jimenez", "Carmona", "Barrios", "Padilla", "Correa", "Acosta",
        "Navarro", "Pacheco", "Ibarra", "Florez", "Quintero", "Molina", "De La Hoz", "Polo",
        "Borrero", "Paternina", "Cervantes", "Consuegra", "Teheran", "Rangel", "Arrieta", "Ospino",
    ]

    SUBJECT_CATALOG = [
        ("Matematicas", 4),
        ("Lengua Castellana", 4),
        ("Ciencias Naturales", 3),
        ("Ciencias Sociales", 3),
        ("Ingles", 3),
        ("Tecnologia e Informatica", 2),
        ("Emprendimiento", 1),
        ("Base de Datos", 2),
        ("Programacion Python", 2),
    ]

    LOWER_PLAN = [
        "Matematicas",
        "Lengua Castellana",
        "Ciencias Naturales",
        "Ciencias Sociales",
        "Ingles",
        "Tecnologia e Informatica",
        "Emprendimiento",
    ]
    UPPER_PLAN = LOWER_PLAN + ["Base de Datos", "Programacion Python"]

    SUBJECT_TEACHERS = {
        "Matematicas": ["doc_matematicas", "doc_matematicas_apoyo", "doc_matematicas_3"],
        "Lengua Castellana": ["doc_lengua", "doc_lengua_apoyo", "doc_lengua_3"],
        "Ciencias Naturales": ["doc_ciencias", "doc_ciencias_apoyo", "doc_ciencias_3"],
        "Ciencias Sociales": ["doc_sociales", "doc_sociales_apoyo", "doc_sociales_3"],
        "Ingles": ["doc_ingles", "doc_ingles_apoyo", "doc_ingles_3"],
        "Tecnologia e Informatica": ["doc_tecnologia", "doc_tecnologia_2", "doc_tecnologia_3"],
        "Emprendimiento": ["doc_emprendimiento", "doc_emprendimiento_2"],
        "Base de Datos": ["doc_bdatos", "doc_bdatos_2", "doc_bdatos_3"],
        "Programacion Python": ["doc_python", "doc_python_2", "doc_python_3"],
    }

    GROUPS = [(str(grado), grupo) for grado in range(6, 12) for grupo in ("A", "B")]

    EXTRA_ACTIVITY_TEMPLATES = {
        "tecnologia e informatica": {
            ActividadEvaluativa.DIMENSION_PARCIAL: [
                "Parcial 1: herramientas digitales y ciudadania",
                "Parcial 2: produccion de contenidos y presentaciones",
            ],
            ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                "Guia de herramientas ofimaticas",
                "Taller de procesador de texto",
                "Practica de hojas de calculo",
                "Proyecto corto de presentacion digital",
            ],
            ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                "Participacion responsable en TIC",
                "Organizacion y cumplimiento en laboratorio",
            ],
        },
        "emprendimiento": {
            ActividadEvaluativa.DIMENSION_PARCIAL: [
                "Parcial 1: ideas de negocio y entorno",
                "Parcial 2: propuesta de valor y costos",
            ],
            ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                "Mapa de ideas emprendedoras",
                "Taller de modelo de negocio",
                "Pitch de producto o servicio",
                "Actividad de mercadeo basico",
            ],
            ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                "Liderazgo y trabajo colaborativo",
                "Compromiso y seguimiento del proyecto",
            ],
        },
        "base de datos": {
            ActividadEvaluativa.DIMENSION_PARCIAL: [
                "Parcial 1: modelo entidad relacion",
                "Parcial 2: consultas y normalizacion",
            ],
            ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                "Diseno del modelo de datos",
                "Taller de cardinalidad y atributos",
                "Practica de consultas SQL",
                "Laboratorio de tablas y relaciones",
            ],
            ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                "Rigor en documentacion tecnica",
                "Responsabilidad en laboratorio de BD",
            ],
        },
        "programacion python": {
            ActividadEvaluativa.DIMENSION_PARCIAL: [
                "Parcial 1: sintaxis, variables y condicionales",
                "Parcial 2: funciones, listas y solucion de problemas",
            ],
            ActividadEvaluativa.DIMENSION_ACTIVIDADES: [
                "Taller de pseudocodigo y algoritmos",
                "Practica guiada de estructuras de control",
                "Laboratorio de funciones y listas",
                "Mini proyecto en Python",
            ],
            ActividadEvaluativa.DIMENSION_ACTITUDINAL: [
                "Participacion y depuracion responsable",
                "Cumplimiento y orden del codigo",
            ],
        },
    }

    PERIOD_ACTIVITY_LAYOUT = {
        ActividadEvaluativa.DIMENSION_ACTITUDINAL: [0.08, 0.58],
        ActividadEvaluativa.DIMENSION_ACTIVIDADES: [0.18, 0.30, 0.42, 0.67],
        ActividadEvaluativa.DIMENSION_PARCIAL: [0.50, 0.84],
    }

    def handle(self, *args, **options):
        self.random = Random(20260429)

        with transaction.atomic():
            anio = self.ensure_academic_year()
            periodos = self.ensure_periods(anio)
            docentes = self.ensure_teachers()
            asignaturas = self.ensure_subjects()
            grupos = self.ensure_groups(docentes)
            estudiantes = self.ensure_students(grupos)
            cargas = self.ensure_cargas(anio, grupos, asignaturas, docentes)
            self.reset_academic_tracking(cargas)
            actividades = self.ensure_activities(periodos, cargas)
            self.ensure_grades(actividades)
            asegurar_configuraciones_inasistencia()
            asegurar_configuraciones_alertas_academicas()

        self.stdout.write(self.style.SUCCESS("Institucion completa poblada correctamente."))
        self.stdout.write(f"Grupos activos preparados: {len(grupos)}")
        self.stdout.write(f"Estudiantes activos preparados: {len(estudiantes)}")
        self.stdout.write(f"Cargas academicas activas preparadas: {len(cargas)}")
        self.stdout.write(f"Actividades creadas: {len(actividades)}")

    def ensure_academic_year(self):
        anio, _ = AnioLectivo.objects.get_or_create(anio=2026, defaults={"activo": True})
        if not anio.activo:
            anio.activo = True
            anio.save(update_fields=["activo"])
        return anio

    def ensure_periods(self, anio):
        periodos_data = [
            ("PERIODO 1", 1, date(2026, 1, 27), date(2026, 4, 10), False),
            ("PERIODO 2", 2, date(2026, 4, 13), date(2026, 6, 19), True),
            ("PERIODO 3", 3, date(2026, 7, 7), date(2026, 9, 11), False),
            ("PERIODO 4", 4, date(2026, 9, 14), date(2026, 11, 27), False),
        ]
        periodos = {}
        for nombre, numero, inicio, fin, activo in periodos_data:
            periodo, _ = PeriodoAcademico.objects.get_or_create(
                anio_lectivo=anio,
                numero=numero,
                defaults={
                    "nombre": nombre,
                    "fecha_inicio": inicio,
                    "fecha_fin": fin,
                    "activo": activo,
                },
            )
            updates = []
            if periodo.nombre != nombre:
                periodo.nombre = nombre
                updates.append("nombre")
            if periodo.fecha_inicio != inicio:
                periodo.fecha_inicio = inicio
                updates.append("fecha_inicio")
            if periodo.fecha_fin != fin:
                periodo.fecha_fin = fin
                updates.append("fecha_fin")
            if periodo.activo != activo:
                periodo.activo = activo
                updates.append("activo")
            if updates:
                periodo.save(update_fields=updates)
            periodos[numero] = periodo
        return periodos

    def ensure_teachers(self):
        user_model = get_user_model()
        docentes = {}
        for username, first_name, last_name, telefono in self.DOCENTES:
            docente, _ = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{username}@colegio.edu.co",
                    "rol": "DOC",
                    "is_staff": True,
                    "is_active": True,
                    "telefono": telefono,
                },
            )
            docente.first_name = first_name
            docente.last_name = last_name
            docente.email = f"{username}@colegio.edu.co"
            docente.rol = "DOC"
            docente.is_staff = True
            docente.is_active = True
            if hasattr(docente, "telefono"):
                docente.telefono = telefono
            docente.set_password("Docente2026*")
            docente.save()
            docentes[username] = docente
        return docentes

    def ensure_subjects(self):
        asignaturas = {}
        for nombre, intensidad in self.SUBJECT_CATALOG:
            asignatura, _ = Asignatura.objects.get_or_create(
                nombre=nombre,
                defaults={"intensidad_horaria": intensidad, "activa": True},
            )
            updates = []
            if asignatura.intensidad_horaria != intensidad:
                asignatura.intensidad_horaria = intensidad
                updates.append("intensidad_horaria")
            if not asignatura.activa:
                asignatura.activa = True
                updates.append("activa")
            if updates:
                asignatura.save(update_fields=updates)
            asignaturas[nombre] = asignatura
        return asignaturas

    def ensure_groups(self, docentes):
        grupos = []
        director_usernames = [
            "doc_lengua", "doc_matematicas", "doc_ciencias", "doc_sociales",
            "doc_ingles", "doc_tecnologia", "doc_lengua_apoyo", "doc_matematicas_apoyo",
            "doc_ciencias_apoyo", "doc_sociales_apoyo", "doc_bdatos", "doc_python",
        ]
        for index, (grado_nombre, grupo_nombre) in enumerate(self.GROUPS):
            grado, _ = Grado.objects.get_or_create(nombre=grado_nombre)
            grupo, _ = Grupo.objects.get_or_create(
                grado=grado,
                nombre=grupo_nombre,
                defaults={"activo": True},
            )
            updates = []
            if not grupo.activo:
                grupo.activo = True
                updates.append("activo")
            director = docentes[director_usernames[index % len(director_usernames)]]
            if grupo.director_grupo_id != director.id:
                grupo.director_grupo = director
                updates.append("director_grupo")
            if updates:
                grupo.save(update_fields=updates)
            grupos.append(grupo)
        return grupos

    def ensure_students(self, grupos):
        estudiantes_resultado = []
        for index, grupo in enumerate(grupos):
            activos = list(grupo.estudiantes.filter(activo=True).order_by("fecha_registro", "id"))
            if len(activos) > 30:
                for estudiante in activos[30:]:
                    estudiante.activo = False
                    estudiante.save(update_fields=["activo"])
                activos = activos[:30]

            while len(activos) < 30:
                numero = len(activos) + 1
                genero = "M" if ((numero + index) % 2 == 0) else "F"
                nombres = self.build_names(genero, numero, index)
                apellidos = self.build_last_names(numero, index)
                documento = self.generate_document(grupo, numero)
                correo_base = (
                    f"{nombres.split()[0].lower()}.{apellidos.split()[0].lower()}."
                    f"{grupo.grado.nombre}{grupo.nombre}{numero:02d}"
                ).replace(" ", "")
                birth_date = self.generate_birthdate(grupo.grado.nombre, numero, index)

                estudiante, _ = Estudiante.objects.get_or_create(
                    documento=documento,
                    defaults={
                        "tipo_documento": "TI",
                        "nombres": nombres,
                        "apellidos": apellidos,
                        "genero": inferir_genero_por_nombre(nombres.split()[0]),
                        "fecha_nacimiento": birth_date,
                        "grupo": grupo,
                        "correo": f"{correo_base}@estudiante.edu.co",
                        "whatsapp": self.generate_phone("300", grupo, numero),
                        "acudiente": self.generate_guardian_name(apellidos, numero, index),
                        "correo_acudiente": f"familia.{correo_base}@acudiente.com",
                        "telefono_acudiente": self.generate_phone("301", grupo, numero),
                        "whatsapp_acudiente": self.generate_phone("302", grupo, numero),
                        "direccion": self.generate_address(numero, index),
                        "activo": True,
                    },
                )
                updates = []
                if estudiante.nombres != nombres:
                    estudiante.nombres = nombres
                    updates.append("nombres")
                if estudiante.apellidos != apellidos:
                    estudiante.apellidos = apellidos
                    updates.append("apellidos")
                genero_inferido = inferir_genero_por_nombre(nombres.split()[0])
                if estudiante.genero != genero_inferido:
                    estudiante.genero = genero_inferido
                    updates.append("genero")
                if estudiante.fecha_nacimiento != birth_date:
                    estudiante.fecha_nacimiento = birth_date
                    updates.append("fecha_nacimiento")
                if estudiante.grupo_id != grupo.id:
                    estudiante.grupo = grupo
                    updates.append("grupo")
                if estudiante.correo != f"{correo_base}@estudiante.edu.co":
                    estudiante.correo = f"{correo_base}@estudiante.edu.co"
                    updates.append("correo")
                telefono = self.generate_phone("300", grupo, numero)
                if estudiante.whatsapp != telefono:
                    estudiante.whatsapp = telefono
                    updates.append("whatsapp")
                acudiente = self.generate_guardian_name(apellidos, numero, index)
                if estudiante.acudiente != acudiente:
                    estudiante.acudiente = acudiente
                    updates.append("acudiente")
                correo_acudiente = f"familia.{correo_base}@acudiente.com"
                if estudiante.correo_acudiente != correo_acudiente:
                    estudiante.correo_acudiente = correo_acudiente
                    updates.append("correo_acudiente")
                tel_acudiente = self.generate_phone("301", grupo, numero)
                if estudiante.telefono_acudiente != tel_acudiente:
                    estudiante.telefono_acudiente = tel_acudiente
                    updates.append("telefono_acudiente")
                wa_acudiente = self.generate_phone("302", grupo, numero)
                if estudiante.whatsapp_acudiente != wa_acudiente:
                    estudiante.whatsapp_acudiente = wa_acudiente
                    updates.append("whatsapp_acudiente")
                direccion = self.generate_address(numero, index)
                if estudiante.direccion != direccion:
                    estudiante.direccion = direccion
                    updates.append("direccion")
                if not estudiante.activo:
                    estudiante.activo = True
                    updates.append("activo")
                if updates:
                    estudiante.save(update_fields=updates)
                activos.append(estudiante)

            estudiantes_resultado.extend(activos)
        return estudiantes_resultado

    def ensure_cargas(self, anio, grupos, asignaturas, docentes):
        cargas = []
        for index, grupo in enumerate(grupos):
            plan = self.plan_for_grade(grupo.grado.nombre)
            for nombre_asignatura in plan:
                asignatura = asignaturas[nombre_asignatura]
                docente = self.select_teacher_for_group(docentes, nombre_asignatura, index)
                existentes = list(CargaAcademica.objects.filter(
                    grupo=grupo,
                    asignatura=asignatura,
                    anio_lectivo=anio,
                ).order_by("id"))
                if existentes:
                    carga = existentes[0]
                    updates = []
                    if carga.docente_id != docente.id:
                        carga.docente = docente
                        updates.append("docente")
                    if not carga.activo:
                        carga.activo = True
                        updates.append("activo")
                    if updates:
                        carga.save(update_fields=updates)
                    for extra in existentes[1:]:
                        if extra.activo:
                            extra.activo = False
                            extra.save(update_fields=["activo"])
                    cargas.append(carga)
                else:
                    carga = CargaAcademica.objects.create(
                        docente=docente,
                        grupo=grupo,
                        asignatura=asignatura,
                        anio_lectivo=anio,
                        activo=True,
                    )
                    cargas.append(carga)
        return cargas

    def reset_academic_tracking(self, cargas):
        carga_ids = [carga.id for carga in cargas]
        if not carga_ids:
            return
        Asistencia.objects.filter(carga_academica_id__in=carga_ids).delete()
        ActividadEvaluativa.objects.filter(carga_academica_id__in=carga_ids).delete()

    def ensure_activities(self, periodos, cargas):
        actividades = []
        for carga in cargas:
            grado = self.grade_number(carga.grupo.grado.nombre)
            plantillas = self.activity_templates_for_subject(carga.asignatura.nombre, grado)
            for periodo in periodos.values():
                fechas = self.distribute_period_dates(periodo)
                for dimension, nombres in plantillas.items():
                    porcentajes = repartir_porcentajes(len(nombres))
                    for nombre, porcentaje, fecha in zip(nombres, porcentajes, fechas[dimension]):
                        actividad = ActividadEvaluativa.objects.create(
                            carga_academica=carga,
                            periodo=periodo,
                            nombre=nombre,
                            dimension=dimension,
                            porcentaje=porcentaje,
                            fecha=fecha,
                            activa=True,
                        )
                        actividades.append(actividad)
        return actividades

    def ensure_grades(self, actividades):
        subject_bias = {
            "Matematicas": Decimal("-0.18"),
            "Lengua Castellana": Decimal("0.08"),
            "Ciencias Naturales": Decimal("-0.05"),
            "Ciencias Sociales": Decimal("0.10"),
            "Ingles": Decimal("-0.08"),
            "Tecnologia e Informatica": Decimal("0.06"),
            "Emprendimiento": Decimal("0.12"),
            "Base de Datos": Decimal("0.02"),
            "Programacion Python": Decimal("-0.02"),
        }
        dimension_bias = {
            ActividadEvaluativa.DIMENSION_PARCIAL: Decimal("-0.08"),
            ActividadEvaluativa.DIMENSION_ACTIVIDADES: Decimal("0.04"),
            ActividadEvaluativa.DIMENSION_ACTITUDINAL: Decimal("0.10"),
        }
        for actividad in actividades:
            estudiantes = Estudiante.objects.filter(
                grupo=actividad.carga_academica.grupo,
                activo=True,
            ).order_by("apellidos", "nombres")
            ajuste_asignatura = subject_bias.get(actividad.carga_academica.asignatura.nombre, Decimal("0"))
            ajuste_dimension = dimension_bias.get(actividad.dimension, Decimal("0"))
            ajuste_periodo = Decimal(str(round((actividad.periodo.numero - 1) * 0.05, 2)))

            for posicion, estudiante in enumerate(estudiantes, start=1):
                if posicion <= 5:
                    base_score = self.random.uniform(1.9, 2.9)
                elif posicion <= 12:
                    base_score = self.random.uniform(2.8, 3.6)
                elif posicion <= 24:
                    base_score = self.random.uniform(3.4, 4.3)
                else:
                    base_score = self.random.uniform(4.0, 4.8)

                nota = Decimal(str(round(base_score, 2)))
                nota = (nota + ajuste_asignatura + ajuste_dimension + ajuste_periodo).quantize(Decimal("0.01"))
                nota = max(Decimal("1.50"), min(Decimal("5.00"), nota))

                Calificacion.objects.create(
                    actividad=actividad,
                    estudiante=estudiante,
                    nota=nota,
                    observacion="Requiere acompanamiento" if nota < Decimal("3.00") else "Desempeno acorde al seguimiento.",
                )

    def plan_for_grade(self, grado_nombre):
        return self.LOWER_PLAN if self.grade_number(grado_nombre) <= 8 else self.UPPER_PLAN

    def select_teacher_for_group(self, docentes, asignatura, group_index):
        pool = self.SUBJECT_TEACHERS[asignatura]
        username = pool[group_index % len(pool)]
        return docentes[username]

    def activity_templates_for_subject(self, asignatura, grado):
        asignatura_normalizada = (asignatura or "").strip().lower()
        if asignatura_normalizada in self.EXTRA_ACTIVITY_TEMPLATES:
            return self.EXTRA_ACTIVITY_TEMPLATES[asignatura_normalizada]

        plantillas = obtener_plantillas(asignatura, grado)
        return {
            ActividadEvaluativa.DIMENSION_PARCIAL: plantillas[ActividadEvaluativa.DIMENSION_PARCIAL][:2],
            ActividadEvaluativa.DIMENSION_ACTIVIDADES: plantillas[ActividadEvaluativa.DIMENSION_ACTIVIDADES][:4],
            ActividadEvaluativa.DIMENSION_ACTITUDINAL: plantillas[ActividadEvaluativa.DIMENSION_ACTITUDINAL][:2],
        }

    def distribute_period_dates(self, periodo):
        total_days = max((periodo.fecha_fin - periodo.fecha_inicio).days, 1)
        fechas = {}
        for dimension, ratios in self.PERIOD_ACTIVITY_LAYOUT.items():
            fechas_dimension = []
            for ratio in ratios:
                fecha = periodo.fecha_inicio + timedelta(days=min(int(total_days * ratio), total_days))
                if fecha.weekday() >= 5:
                    fecha += timedelta(days=(7 - fecha.weekday()) % 7)
                    if fecha > periodo.fecha_fin:
                        fecha = periodo.fecha_fin
                fechas_dimension.append(fecha)
            fechas[dimension] = fechas_dimension
        return fechas

    def grade_number(self, grado_nombre):
        try:
            return int(grado_nombre)
        except (TypeError, ValueError):
            return 0

    def build_names(self, genero, numero, index):
        banco = self.MALE_NAMES if genero == "M" else self.FEMALE_NAMES
        primer = banco[(numero + index * 3) % len(banco)]
        segundo_banco = self.MALE_NAMES + self.FEMALE_NAMES
        segundo = segundo_banco[(numero * 2 + index * 5) % len(segundo_banco)]
        if segundo == primer:
            segundo = segundo_banco[(numero * 2 + index * 5 + 7) % len(segundo_banco)]
        return f"{primer} {segundo}"

    def build_last_names(self, numero, index):
        apellido_1 = self.LAST_NAMES[(numero + index * 4) % len(self.LAST_NAMES)]
        apellido_2 = self.LAST_NAMES[(numero * 3 + index * 7 + 5) % len(self.LAST_NAMES)]
        if apellido_1 == apellido_2:
            apellido_2 = self.LAST_NAMES[(numero * 5 + index * 9 + 3) % len(self.LAST_NAMES)]
        return f"{apellido_1} {apellido_2}"

    def generate_document(self, grupo, numero):
        group_code = "1" if grupo.nombre.upper() == "A" else "2"
        return f"10{int(grupo.grado.nombre):02d}{group_code}{numero:05d}"

    def generate_birthdate(self, grado_nombre, numero, index):
        edades = {
            "6": (11, 12),
            "7": (12, 13),
            "8": (13, 14),
            "9": (14, 15),
            "10": (15, 16),
            "11": (16, 17),
        }
        edad_min, edad_max = edades[grado_nombre]
        birth_year = 2026 - self.random.randint(edad_min, edad_max)
        birth_month = ((numero + index) % 12) + 1
        birth_day = ((numero * 2 + index) % 27) + 1
        return date(birth_year, birth_month, birth_day)

    def generate_guardian_name(self, apellidos, numero, index):
        banco = self.FEMALE_NAMES + self.MALE_NAMES
        nombre = banco[(numero + index * 2 + 4) % len(banco)]
        apellido = apellidos.split()[0]
        return f"{nombre} {apellido}"

    def generate_phone(self, prefix, grupo, numero):
        group_code = "1" if grupo.nombre.upper() == "A" else "2"
        return f"{prefix}{int(grupo.grado.nombre):02d}{group_code}{numero:04d}"

    def generate_address(self, numero, index):
        via = 10 + ((numero + index) % 80)
        placa_1 = 1 + ((numero * 3 + index) % 90)
        placa_2 = 1 + ((numero * 5 + index) % 95)
        barrio = [
            "Centro", "La Playa", "Boston", "Silencio",
            "San Felipe", "Ciudadela", "El Prado", "Las Nieves",
        ][(numero + index) % 8]
        return f"Calle {via} # {placa_1}-{placa_2}, Barrio {barrio}, Atlantico"
