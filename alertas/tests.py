from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from academico.models import AnioLectivo, Asignatura, CargaAcademica, Estudiante, Grado, Grupo, PeriodoAcademico
from asistencia.models import Asistencia
from evaluacion.models import ActividadEvaluativa, Calificacion
from .models import AlertaTemprana, SeguimientoAlerta, TipoAlerta
from .utils import evaluar_alertas_academicas


class AlertasAcademicasTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.docente = User.objects.create_user(username='docente_alertas', password='test12345', rol='DOC')
        self.anio = AnioLectivo.objects.create(anio=2026)
        self.periodo = PeriodoAcademico.objects.create(
            nombre='Primer periodo',
            numero=1,
            fecha_inicio=date(2026, 1, 27),
            fecha_fin=date(2026, 4, 10),
            anio_lectivo=self.anio,
        )
        self.grado = Grado.objects.create(nombre='10')
        self.grupo = Grupo.objects.create(nombre='A', grado=self.grado)
        self.asignatura = Asignatura.objects.create(nombre='Matematicas', intensidad_horaria=5)
        self.carga = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        self.estudiante = Estudiante.objects.create(
            tipo_documento='TI',
            documento='200001',
            nombres='Carlos Andres',
            apellidos='Gomez Perez',
            fecha_nacimiento=date(2010, 3, 20),
            grupo=self.grupo,
            acudiente='Marta Perez',
            telefono_acudiente='3001234567',
        )
        self.actividad = ActividadEvaluativa.objects.create(
            carga_academica=self.carga,
            periodo=self.periodo,
            nombre='Evaluacion',
            dimension=ActividadEvaluativa.DIMENSION_PARCIAL,
            porcentaje=Decimal('100.00'),
            fecha=date(2026, 3, 1),
        )

    def test_genera_alerta_bajo_rendimiento(self):
        Calificacion.objects.create(
            estudiante=self.estudiante,
            actividad=self.actividad,
            nota=Decimal('2.50'),
        )

        evaluar_alertas_academicas(self.estudiante)

        self.assertTrue(
            AlertaTemprana.objects.filter(
                estudiante=self.estudiante,
                tipo_alerta__nombre='Bajo rendimiento academico',
                estado='ACTIVA',
                nivel='RIESGO',
            ).exists()
        )

    def test_genera_alerta_riesgo_integral(self):
        Calificacion.objects.create(
            estudiante=self.estudiante,
            actividad=self.actividad,
            nota=Decimal('2.50'),
        )
        for offset in range(3):
            Asistencia.objects.create(
                estudiante=self.estudiante,
                carga_academica=self.carga,
                fecha=date(2026, 3, 1 + offset),
                estado='A',
            )

        evaluar_alertas_academicas(self.estudiante)

        self.assertTrue(
            AlertaTemprana.objects.filter(
                estudiante=self.estudiante,
                tipo_alerta__nombre='Riesgo integral academico',
                estado='ACTIVA',
                nivel='CRITICO',
            ).exists()
        )

    def test_registra_seguimiento_de_alerta(self):
        tipo_alerta = TipoAlerta.objects.create(nombre='Prueba seguimiento')
        alerta = AlertaTemprana.objects.create(
            estudiante=self.estudiante,
            tipo_alerta=tipo_alerta,
            nivel='RIESGO',
            descripcion='Riesgo academico detectado.',
            estado='ACTIVA',
        )
        self.client.force_login(self.docente)

        response = self.client.post(f'/alertas/{alerta.id}/', {
            'accion': 'CONTACTO_ACUDIENTE',
            'descripcion': 'Se contacto al acudiente y se acordo acompanamiento semanal.',
            'resultado': 'EN_PROCESO',
            'proxima_revision': '2026-04-20',
        })

        alerta.refresh_from_db()
        self.assertRedirects(response, f'/alertas/{alerta.id}/')
        self.assertEqual(alerta.estado, 'REVISADA')
        self.assertTrue(
            SeguimientoAlerta.objects.filter(
                alerta=alerta,
                registrado_por=self.docente,
                accion='CONTACTO_ACUDIENTE',
            ).exists()
        )

    def test_detalle_alerta_muestra_inasistencias_especificas(self):
        for offset in range(5):
            Asistencia.objects.create(
                estudiante=self.estudiante,
                carga_academica=self.carga,
                fecha=date(2026, 3, 1 + offset),
                estado='A',
                observacion='Ausencia registrada',
            )

        evaluar_alertas_academicas(self.estudiante)
        alerta = AlertaTemprana.objects.get(
            estudiante=self.estudiante,
            tipo_alerta__nombre='Inasistencia acumulada',
        )

        self.client.force_login(self.docente)
        response = self.client.get(f'/alertas/{alerta.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detalle de inasistencias acumuladas')
        self.assertContains(response, '2026-03-05')
        self.assertContains(response, 'Matematicas')
        self.assertContains(response, 'Ausencia registrada')
