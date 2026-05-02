from datetime import date, time

from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from academico.models import AnioLectivo, Asignatura, CargaAcademica, Estudiante, Grado, Grupo, HorarioClase


class ExportesExcelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin_exportes',
            password='testpass123',
            rol='ADMIN',
        )
        self.client.force_login(self.user)

    def test_exportar_alertas_excel(self):
        response = self.client.get('/alertas/exportar/excel/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_exportar_resumen_calificaciones_excel(self):
        response = self.client.get('/evaluacion/resumen/exportar/excel/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_exportar_estudiantes_riesgo_excel(self):
        response = self.client.get('/exportar-riesgo/excel/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


class DashboardRenderTests(TestCase):
    def test_dashboard_renderiza_para_admin(self):
        user = get_user_model().objects.create_user(
            username='admin_dashboard',
            password='testpass123',
            rol='ADMIN',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('inicio'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard ejecutivo')
        if settings.POWERBI_DASHBOARD_URL:
            self.assertContains(response, 'Tablero analitico institucional')
            self.assertContains(response, 'pageView=fitToWidth')
        else:
            self.assertContains(response, 'Tablero externo pendiente')

    def test_dashboard_renderiza_para_docente(self):
        user = get_user_model().objects.create_user(
            username='doc_dashboard',
            password='testpass123',
            rol='DOC',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('inicio'))

        self.assertEqual(response.status_code, 200)
        if settings.POWERBI_DASHBOARD_URL:
            self.assertContains(response, 'Tablero analitico institucional')
        else:
            self.assertContains(response, 'Tablero externo pendiente')

    def test_dashboard_renderiza_para_estudiante(self):
        user = get_user_model().objects.create_user(
            username='est_dashboard',
            password='testpass123',
            rol='EST',
        )
        anio = AnioLectivo.objects.create(anio=2026)
        grado = Grado.objects.create(nombre='9')
        grupo = Grupo.objects.create(nombre='A', grado=grado)
        Estudiante.objects.create(
            usuario=user,
            tipo_documento='TI',
            documento='12345678',
            nombres='Laura',
            apellidos='Martinez',
            fecha_nacimiento=date(2011, 4, 10),
            grupo=grupo,
            acudiente='Marta Martinez',
            telefono_acudiente='3001234567',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('inicio'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mi panel academico')
        self.assertContains(response, 'Mi horario')

    def test_horario_estudiante_no_permite_filtrar_por_docente(self):
        User = get_user_model()
        estudiante_user = User.objects.create_user(
            username='est_horario',
            password='testpass123',
            rol='EST',
        )
        docente_1 = User.objects.create_user(
            username='doc_horario_1',
            password='testpass123',
            rol='DOC',
            first_name='Carlos',
            last_name='Lopez',
        )
        docente_2 = User.objects.create_user(
            username='doc_horario_2',
            password='testpass123',
            rol='DOC',
            first_name='Maria',
            last_name='Gomez',
        )
        anio = AnioLectivo.objects.create(anio=2027)
        grado = Grado.objects.create(nombre='10')
        grupo = Grupo.objects.create(nombre='B', grado=grado)
        otro_grupo = Grupo.objects.create(nombre='A', grado=grado)
        estudiante = Estudiante.objects.create(
            usuario=estudiante_user,
            tipo_documento='TI',
            documento='87654321',
            nombres='Laura',
            apellidos='Perez',
            fecha_nacimiento=date(2010, 6, 15),
            grupo=grupo,
            acudiente='Ana Perez',
            telefono_acudiente='3009990000',
        )
        asignatura = Asignatura.objects.create(nombre='Historia')
        otra_asignatura = Asignatura.objects.create(nombre='Fisica')
        carga_grupo = CargaAcademica.objects.create(
            docente=docente_1,
            grupo=grupo,
            asignatura=asignatura,
            anio_lectivo=anio,
        )
        carga_otra = CargaAcademica.objects.create(
            docente=docente_2,
            grupo=otro_grupo,
            asignatura=otra_asignatura,
            anio_lectivo=anio,
        )
        HorarioClase.objects.create(
            carga_academica=carga_grupo,
            dia_semana=1,
            hora_inicio=time(7, 0),
            hora_fin=time(7, 50),
            aula='Aula 1',
        )
        HorarioClase.objects.create(
            carga_academica=carga_otra,
            dia_semana=1,
            hora_inicio=time(8, 0),
            hora_fin=time(8, 50),
            aula='Aula 2',
        )
        self.client.force_login(estudiante_user)

        response = self.client.get(reverse('horarios_academicos'), {'docente': docente_2.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(estudiante.grupo))
        self.assertNotContains(response, str(otro_grupo))
        self.assertContains(response, 'Docentes de')
