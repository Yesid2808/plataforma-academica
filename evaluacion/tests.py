from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from academico.models import AnioLectivo, Asignatura, CargaAcademica, Estudiante, Grado, Grupo, PeriodoAcademico
from usuarios.models import NotificacionUsuario
from .models import ActividadEvaluativa, Calificacion
from .utils import calcular_promedio_dimensionado


class EvaluacionPermisosTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.docente = User.objects.create_user(username='doc_eval', password='test12345', rol='DOC')
        self.otro_docente = User.objects.create_user(username='otro_doc_eval', password='test12345', rol='DOC')
        self.anio = AnioLectivo.objects.create(anio=2026)
        self.periodo = PeriodoAcademico.objects.create(
            nombre='Primer periodo',
            numero=1,
            fecha_inicio=date(2026, 1, 27),
            fecha_fin=date(2026, 4, 10),
            anio_lectivo=self.anio,
        )
        self.grado = Grado.objects.create(nombre='8')
        self.grupo = Grupo.objects.create(nombre='B', grado=self.grado)
        self.asignatura = Asignatura.objects.create(nombre='Matematicas')
        self.otra_asignatura = Asignatura.objects.create(nombre='Ciencias')
        self.carga = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        self.carga_ajena = CargaAcademica.objects.create(
            docente=self.otro_docente,
            grupo=self.grupo,
            asignatura=self.otra_asignatura,
            anio_lectivo=self.anio,
        )
        self.actividad = ActividadEvaluativa.objects.create(
            carga_academica=self.carga,
            periodo=self.periodo,
            nombre='Quiz',
            dimension=ActividadEvaluativa.DIMENSION_PARCIAL,
            porcentaje=Decimal('50.00'),
            fecha=date(2026, 3, 1),
        )
        self.actividad_ajena = ActividadEvaluativa.objects.create(
            carga_academica=self.carga_ajena,
            periodo=self.periodo,
            nombre='Taller',
            dimension=ActividadEvaluativa.DIMENSION_PARCIAL,
            porcentaje=Decimal('50.00'),
            fecha=date(2026, 3, 2),
        )
        Estudiante.objects.create(
            tipo_documento='TI',
            documento='300001',
            nombres='Sofia',
            apellidos='Ramirez',
            fecha_nacimiento=date(2011, 1, 1),
            grupo=self.grupo,
            acudiente='Ana Ramirez',
            telefono_acudiente='3001234567',
        )
        self.estudiante = Estudiante.objects.create(
            tipo_documento='TI',
            documento='300002',
            nombres='Mateo',
            apellidos='Castro',
            fecha_nacimiento=date(2011, 2, 1),
            grupo=self.grupo,
            acudiente='Julia Castro',
            telefono_acudiente='3008887766',
        )
        self.coordinador = User.objects.create_user(username='coord_eval', password='test12345', rol='COORD')

    def test_docente_accede_a_su_actividad(self):
        self.client.force_login(self.docente)
        response = self.client.get(reverse('registrar_calificaciones', args=[self.actividad.id]))
        self.assertEqual(response.status_code, 200)

    def test_docente_no_accede_a_actividad_ajena(self):
        self.client.force_login(self.docente)
        response = self.client.get(reverse('registrar_calificaciones', args=[self.actividad_ajena.id]))
        self.assertEqual(response.status_code, 404)

    def test_modificar_calificacion_docente_genera_notificacion(self):
        Calificacion.objects.create(
            actividad=self.actividad,
            estudiante=self.estudiante,
            nota=Decimal('3.00'),
            observacion='Inicial',
        )
        self.client.force_login(self.docente)

        response = self.client.post(reverse('registrar_calificaciones', args=[self.actividad.id]), {
            f'nota_{self.estudiante.id}': '2.50',
            f'observacion_{self.estudiante.id}': 'Ajuste docente',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            NotificacionUsuario.objects.filter(
                usuario=self.coordinador,
                tipo='CALIFICACION',
            ).exists()
        )
        self.assertTrue(
            NotificacionUsuario.objects.filter(
                usuario=self.docente,
                tipo='CALIFICACION',
            ).exists()
        )

    def test_formulario_no_permite_superar_dimension(self):
        self.client.force_login(self.docente)

        response = self.client.post(reverse('crear_actividad'), {
            'carga_academica': self.carga.id,
            'periodo': self.periodo.id,
            'dimension': ActividadEvaluativa.DIMENSION_PARCIAL,
            'nombre': 'Segundo parcial',
            'porcentaje': '60.00',
            'fecha': '2026-03-10',
            'activa': 'True',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Esta dimension solo permite distribuir hasta 100% interno')

    def test_promedio_dimensionado_promedia_actividades_por_dimension(self):
        actividad_2 = ActividadEvaluativa.objects.create(
            carga_academica=self.carga,
            periodo=self.periodo,
            nombre='Parcial 2',
            dimension=ActividadEvaluativa.DIMENSION_PARCIAL,
            porcentaje=Decimal('50.00'),
            fecha=date(2026, 3, 5),
        )
        actividad_3 = ActividadEvaluativa.objects.create(
            carga_academica=self.carga,
            periodo=self.periodo,
            nombre='Taller 1',
            dimension=ActividadEvaluativa.DIMENSION_ACTIVIDADES,
            porcentaje=Decimal('100.00'),
            fecha=date(2026, 3, 6),
        )
        actividad_4 = ActividadEvaluativa.objects.create(
            carga_academica=self.carga,
            periodo=self.periodo,
            nombre='Actitud 1',
            dimension=ActividadEvaluativa.DIMENSION_ACTITUDINAL,
            porcentaje=Decimal('100.00'),
            fecha=date(2026, 3, 7),
        )

        cal_1 = Calificacion.objects.create(actividad=self.actividad, estudiante=self.estudiante, nota=Decimal('4.00'))
        cal_2 = Calificacion.objects.create(actividad=actividad_2, estudiante=self.estudiante, nota=Decimal('2.00'))
        cal_3 = Calificacion.objects.create(actividad=actividad_3, estudiante=self.estudiante, nota=Decimal('3.00'))
        cal_4 = Calificacion.objects.create(actividad=actividad_4, estudiante=self.estudiante, nota=Decimal('5.00'))

        promedio, resumen = calcular_promedio_dimensionado([cal_1, cal_2, cal_3, cal_4])

        self.assertEqual(promedio, Decimal('3.40'))
        self.assertEqual(resumen[ActividadEvaluativa.DIMENSION_PARCIAL]['promedio'], Decimal('3.00'))
