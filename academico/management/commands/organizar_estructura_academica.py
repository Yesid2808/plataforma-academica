from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from academico.models import (
    AnioLectivo,
    Asignatura,
    CargaAcademica,
    Estudiante,
    Grado,
    Grupo,
    HorarioClase,
    PeriodoAcademico,
)
from academico.utils import inferir_genero_por_nombre
from alertas.utils import evaluar_alertas_academicas
from asistencia.models import Asistencia
from evaluacion.models import ActividadEvaluativa, Calificacion
from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Organiza docentes, cargas, horarios y datos academicos demo realistas sin cruces.'

    DOCENTES = [
        {
            'username': 'doc_matematicas',
            'password': 'DocMat2026!',
            'first_name': 'Adriana',
            'last_name': 'Fuentes',
            'email': 'doc_matematicas@colegio.edu.co',
            'telefono': '3004001001',
        },
        {
            'username': 'doc_lengua',
            'password': 'DocLen2026!',
            'first_name': 'Ricardo',
            'last_name': 'Benitez',
            'email': 'doc_lengua@colegio.edu.co',
            'telefono': '3004001002',
        },
        {
            'username': 'doc_ciencias',
            'password': 'DocCie2026!',
            'first_name': 'Patricia',
            'last_name': 'Molina',
            'email': 'doc_ciencias@colegio.edu.co',
            'telefono': '3004001003',
        },
        {
            'username': 'doc_sociales',
            'password': 'DocSoc2026!',
            'first_name': 'Jorge',
            'last_name': 'Caballero',
            'email': 'doc_sociales@colegio.edu.co',
            'telefono': '3004001004',
        },
        {
            'username': 'doc_ingles',
            'password': 'DocIng2026!',
            'first_name': 'Claudia',
            'last_name': 'Sarmiento',
            'email': 'doc_ingles@colegio.edu.co',
            'telefono': '3004001005',
        },
        {
    ]

    STUDENTS_8A = [
        ('11008001', 'Samuel David', 'Mendoza Polo'),
        ('11008002', 'Maria Camila', 'Pajaro Castro'),
        ('11008003', 'Juan Esteban', 'Martinez Acosta'),
        ('11008004', 'Valeria', 'Sanchez Payares'),
        ('11008005', 'Miguel Angel', 'Guerra Herrera'),
        ('11008006', 'Sara Isabel', 'Mendoza Ospino'),
        ('11008007', 'Kevin Jose', 'Duarte Ramos'),
        ('11008008', 'Luciana', 'Segrera Barrios'),
        ('11008009', 'Santiago Andres', 'Castro Borrero'),
        ('11008010', 'Daniela', 'Fontalvo Vega'),
        ('11008011', 'Angel David', 'Teheran Rangel'),
        ('11008012', 'Salome', 'Romero Arrieta'),
        ('11008013', 'Jose Manuel', 'Ruiz De La Hoz'),
        ('11008014', 'Mariana', 'Pertuz Cervantes'),
        ('11008015', 'Tomas', 'Pacheco Diaz'),
        ('11008016', 'Gabriela', 'Florez Consuegra'),
        ('11008017', 'Martin Alonso', 'Nieto Figueroa'),
        ('11008018', 'Antonella', 'Molina Bello'),
    ]

    GROUP_SUBJECTS = {
        ('8', 'A'): ['Matematicas', 'Lengua Castellana', 'Ciencias Naturales', 'Ciencias Sociales', 'Ingles'],
        ('8', 'B'): ['Matematicas', 'Lengua Castellana', 'Ciencias Naturales', 'Ciencias Sociales', 'Ingles'],
    }

    SUBJECT_TEACHER = {
        'Matematicas': 'doc_matematicas',
        'Lengua Castellana': 'doc_lengua',
        'Ciencias Naturales': 'doc_ciencias',
        'Ciencias Sociales': 'doc_sociales',
        'Ingles': 'doc_ingles',
    }

    SUBJECT_BLOCKS = {
        'Matematicas': 5,
        'Lengua Castellana': 4,
        'Ciencias Naturales': 4,
        'Ciencias Sociales': 3,
        'Ingles': 3,
    }

    BLOCK_TIMES = [
        (time(6, 30), time(7, 20)),
        (time(7, 20), time(8, 10)),
        (time(8, 25), time(9, 15)),
        (time(9, 15), time(10, 5)),
        (time(10, 20), time(11, 10)),
        (time(11, 10), time(12, 0)),
    ]

    AULAS = {
        'Matematicas': 'Salon 201',
        'Lengua Castellana': 'Salon 202',
        'Ciencias Naturales': 'Lab Ciencias',
        'Ciencias Sociales': 'Salon 203',
        'Ingles': 'Language Room',
    }

    ACTIVITY_DATES = [
        date(2026, 3, 18),
        date(2026, 3, 25),
        date(2026, 4, 1),
        date(2026, 4, 8),
    ]

    DATE_START = date(2026, 3, 16)
    DATE_END = date(2026, 4, 10)

    def handle(self, *args, **options):
        with transaction.atomic():
            anio = AnioLectivo.objects.filter(activo=True).order_by('-anio').first()
            if not anio:
                raise RuntimeError('No hay anio lectivo activo.')

            docentes = self._asegurar_docentes()
            grupos = self._obtener_grupos()
            self._completar_estudiantes_8a(grupos[('8', 'A')])
            cargas = self._asegurar_cargas(anio, grupos, docentes)
            self._asignar_directores(grupos, docentes)
            horarios = self._reconstruir_horarios(cargas)
            self._reconstruir_datos_academicos(cargas)

        self.stdout.write(self.style.SUCCESS('Estructura academica organizada correctamente.'))
        self.stdout.write('Credenciales docentes:')
        for docente in self.DOCENTES:
            self.stdout.write(f"- {docente['username']} / {docente['password']}")
        self.stdout.write(f'Bloques horarios creados: {horarios}')

    def _asegurar_docentes(self):
        docentes = {}
        for data in self.DOCENTES:
            user, _ = Usuario.objects.get_or_create(
                username=data['username'],
                defaults={
                    'rol': 'DOC',
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': data['email'],
                    'telefono': data['telefono'],
                }
            )
            user.rol = 'DOC'
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.email = data['email']
            user.telefono = data['telefono']
            user.set_password(data['password'])
            user.save()
            docentes[data['username']] = user
        return docentes

    def _obtener_grupos(self):
        grupos = {}
        for grado_nombre, grupo_nombre in self.GROUP_SUBJECTS:
            grado = Grado.objects.get(nombre=grado_nombre)
            grupos[(grado_nombre, grupo_nombre)] = Grupo.objects.get(grado=grado, nombre=grupo_nombre)
        return grupos

    def _completar_estudiantes_8a(self, grupo):
        existentes = set(Estudiante.objects.filter(grupo=grupo).values_list('documento', flat=True))
        base_year = 2012
        total_actual = Estudiante.objects.filter(grupo=grupo, activo=True).count()

        for offset, (documento, nombres, apellidos) in enumerate(self.STUDENTS_8A, start=1):
            if total_actual >= 25:
                break
            if documento in existentes:
                continue

            genero = inferir_genero_por_nombre(nombres)
            correo_base = f"{nombres.split()[0].lower()}.{apellidos.split()[0].lower()}{documento[-2:]}".replace(' ', '')
            Estudiante.objects.create(
                tipo_documento='TI',
                documento=documento,
                nombres=nombres,
                apellidos=apellidos,
                genero=genero,
                fecha_nacimiento=date(base_year, (offset % 10) + 1, ((offset * 2) % 27) + 1),
                grupo=grupo,
                correo=f'{correo_base}@estudiantes.colegio.edu.co',
                whatsapp=f'30055{offset:05d}',
                acudiente=f'{apellidos.split()[0]} {nombres.split()[0]} Ramirez',
                correo_acudiente=f'familia.{correo_base}@acudientes.edu.co',
                telefono_acudiente=f'30166{offset:05d}',
                whatsapp_acudiente=f'30177{offset:05d}',
                direccion=f'Barrio Modelo, Calle {10 + offset} # {20 + offset}-0{offset % 9 + 1}',
                activo=True,
            )
            total_actual += 1

    def _asegurar_cargas(self, anio, grupos, docentes):
        cargas = {}
        for group_key, subject_names in self.GROUP_SUBJECTS.items():
            grupo = grupos[group_key]
            for subject_name in subject_names:
                asignatura = Asignatura.objects.get(nombre=subject_name)
                docente = docentes[self.SUBJECT_TEACHER[subject_name]]
                carga, _ = CargaAcademica.objects.update_or_create(
                    grupo=grupo,
                    asignatura=asignatura,
                    anio_lectivo=anio,
                    defaults={'docente': docente, 'activo': True},
                )
                cargas[(group_key, subject_name)] = carga
        return cargas

    def _asignar_directores(self, grupos, docentes):
        directores = {
            ('8', 'A'): docentes['doc_lengua'],
            ('8', 'B'): docentes['doc_ciencias'],
        }
        for key, director in directores.items():
            grupo = grupos[key]
            grupo.director_grupo = director
            grupo.save(update_fields=['director_grupo'])

    def _reconstruir_horarios(self, cargas):
        target_cargas = list(cargas.values())
        HorarioClase.objects.filter(carga_academica__in=target_cargas).delete()

        remaining = {
            carga.id: self.SUBJECT_BLOCKS[carga.asignatura.nombre]
            for carga in target_cargas
        }
        carga_lookup = {carga.id: carga for carga in target_cargas}
        group_slots = defaultdict(set)
        teacher_slots = defaultdict(set)
        daily_subjects = defaultdict(lambda: defaultdict(int))
        created = 0

        order_group_keys = list(self.GROUP_SUBJECTS.keys())
        slots = [(day, block) for day in range(1, 6) for block in range(len(self.BLOCK_TIMES))]

        for day, block in slots:
            teacher_used = set()
            for group_index, group_key in enumerate(order_group_keys):
                group = carga_lookup[next(
                    cid for cid, carga in carga_lookup.items()
                    if (carga.grupo.grado.nombre, carga.grupo.nombre) == group_key
                )].grupo
                slot_key = (day, block)
                if slot_key in group_slots[group.id]:
                    continue

                cargas_grupo = [
                    carga for carga in target_cargas
                    if (carga.grupo.grado.nombre, carga.grupo.nombre) == group_key and remaining[carga.id] > 0
                ]
                cargas_grupo.sort(
                    key=lambda carga: (
                        -remaining[carga.id],
                        daily_subjects[group.id][(day, carga.asignatura.nombre)],
                        carga.asignatura.nombre,
                    )
                )

                elegido = None
                for carga in cargas_grupo:
                    docente_id = carga.docente_id
                    if slot_key in teacher_slots[docente_id] or docente_id in teacher_used:
                        continue
                    if daily_subjects[group.id][(day, carga.asignatura.nombre)] >= 2:
                        continue
                    elegido = carga
                    break

                if not elegido:
                    continue

                hora_inicio, hora_fin = self.BLOCK_TIMES[block]
                HorarioClase.objects.create(
                    carga_academica=elegido,
                    dia_semana=day,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    aula=self.AULAS.get(elegido.asignatura.nombre, 'Salon general'),
                )
                remaining[elegido.id] -= 1
                group_slots[group.id].add(slot_key)
                teacher_slots[elegido.docente_id].add(slot_key)
                teacher_used.add(elegido.docente_id)
                daily_subjects[group.id][(day, elegido.asignatura.nombre)] += 1
                created += 1

        if any(value > 0 for value in remaining.values()):
            faltantes = [
                f"{carga_lookup[carga_id].grupo} - {carga_lookup[carga_id].asignatura.nombre}: {cantidad}"
                for carga_id, cantidad in remaining.items() if cantidad > 0
            ]
            raise RuntimeError(f'No fue posible asignar todos los bloques horarios: {faltantes}')

        return created

    def _reconstruir_datos_academicos(self, cargas):
        target_cargas = list(cargas.values())
        target_grupos = {carga.grupo_id for carga in target_cargas}
        estudiantes = list(
            Estudiante.objects.filter(grupo_id__in=target_grupos, activo=True)
            .select_related('grupo', 'grupo__grado')
            .order_by('grupo__grado__nombre', 'grupo__nombre', 'apellidos', 'nombres')
        )

        profiles = self._build_student_profiles(estudiantes)
        Asistencia.objects.filter(
            carga_academica__in=target_cargas,
            fecha__range=(self.DATE_START, self.DATE_END),
        ).delete()
        ActividadEvaluativa.objects.filter(
            carga_academica__in=target_cargas,
            fecha__range=(self.DATE_START, self.DATE_END),
        ).delete()

        horarios_por_carga = defaultdict(list)
        for horario in HorarioClase.objects.filter(carga_academica__in=target_cargas).order_by('dia_semana', 'hora_inicio'):
            horarios_por_carga[horario.carga_academica_id].append(horario)

        for carga in target_cargas:
            alumnos = [est for est in estudiantes if est.grupo_id == carga.grupo_id]
            class_dates = self._class_dates_for_carga(carga, horarios_por_carga[carga.id])

            for fecha_clase in class_dates:
                for estudiante in alumnos:
                    estado, observacion = self._attendance_for_student(estudiante, fecha_clase, profiles[estudiante.id])
                    Asistencia.objects.create(
                        estudiante=estudiante,
                        carga_academica=carga,
                        fecha=fecha_clase,
                        estado=estado,
                        observacion=observacion or None,
                    )

            for idx, fecha_actividad in enumerate(self._activity_dates_for_carga(class_dates), start=1):
                periodo = PeriodoAcademico.objects.filter(
                    fecha_inicio__lte=fecha_actividad,
                    fecha_fin__gte=fecha_actividad,
                ).order_by('fecha_inicio').first()
                if not periodo:
                    continue

                actividad = ActividadEvaluativa.objects.create(
                    carga_academica=carga,
                    periodo=periodo,
                    nombre=f'Seguimiento {idx} {carga.asignatura.nombre}',
                    porcentaje=Decimal('10.00'),
                    fecha=fecha_actividad,
                    activa=True,
                )

                for estudiante in alumnos:
                    Calificacion.objects.create(
                        actividad=actividad,
                        estudiante=estudiante,
                        nota=self._grade_for_student(estudiante, idx, profiles[estudiante.id]),
                        observacion=self._observation_for_profile(profiles[estudiante.id]),
                    )

        for estudiante in estudiantes:
            evaluar_alertas_academicas(estudiante)

    def _build_student_profiles(self, estudiantes):
        by_group = defaultdict(list)
        for estudiante in estudiantes:
            by_group[estudiante.grupo_id].append(estudiante)

        profiles = {}
        for group_students in by_group.values():
            for index, estudiante in enumerate(group_students):
                if index < 4:
                    profile = 'critico'
                elif index < 10:
                    profile = 'riesgo'
                elif index < 16:
                    profile = 'atencion'
                else:
                    profile = 'estable'
                profiles[estudiante.id] = profile
        return profiles

    def _class_dates_for_carga(self, carga, horarios):
        if not horarios:
            return []

        dates = []
        cursor = self.DATE_START
        valid_days = {horario.dia_semana for horario in horarios}
        while cursor <= self.DATE_END:
            if cursor.isoweekday() in valid_days:
                dates.append(cursor)
            cursor += timedelta(days=1)
        return dates

    def _activity_dates_for_carga(self, class_dates):
        return [fecha for fecha in self.ACTIVITY_DATES if fecha in class_dates]

    def _attendance_for_student(self, estudiante, fecha_clase, profile):
        seed = sum(ord(ch) for ch in f'{estudiante.codigo}{fecha_clase.isoformat()}')
        if profile == 'critico' and fecha_clase.day in {17, 24, 31, 7, 10}:
            return 'A', 'Ausencia reiterada. Requiere seguimiento.'
        if profile == 'riesgo' and fecha_clase.day in {18, 25, 8}:
            return 'A', 'Inasistencia periodica.'
        if profile == 'atencion' and fecha_clase.day in {19, 6}:
            return 'T', 'Ingreso tarde a clase.'
        if seed % 19 == 0:
            return 'J', 'Ausencia justificada por acudiente.'
        if seed % 11 == 0:
            return 'T', 'Ingreso tarde registrado.'
        return 'P', ''

    def _grade_for_student(self, estudiante, activity_index, profile):
        base = Decimal(str(((sum(ord(c) for c in estudiante.codigo) + activity_index * 13) % 100) / 100))
        if profile == 'critico':
            value = Decimal('1.50') + (base * Decimal('0.90'))
        elif profile == 'riesgo':
            value = Decimal('2.20') + (base * Decimal('0.90'))
        elif profile == 'atencion':
            value = Decimal('2.95') + (base * Decimal('0.85'))
        else:
            value = Decimal('3.60') + (base * Decimal('1.10'))

        if value > Decimal('5.00'):
            value = Decimal('5.00')
        return value.quantize(Decimal('0.01'))

    def _observation_for_profile(self, profile):
        return {
            'critico': 'Desempeno bajo sostenido. Requiere plan de mejoramiento.',
            'riesgo': 'Presenta vacios y necesita acompanamiento.',
            'atencion': 'Cumple parcialmente; conviene refuerzo preventivo.',
            'estable': 'Buen desempeno y cumplimiento de actividades.',
        }[profile]
