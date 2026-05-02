from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from alertas.models import AlertaTemprana, TipoAlerta
from asistencia.models import Asistencia
from evaluacion.models import ActividadEvaluativa, Calificacion
from .models import (
    AnioLectivo,
    Asignatura,
    CargaAcademica,
    Estudiante,
    Grado,
    Grupo,
    HorarioClase,
    PeriodoAcademico,
    ReporteAcudiente,
)
from .forms import EstudianteUpdateForm
from .utils import inferir_genero_por_nombre


class AcademicoModelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.docente = User.objects.create_user(
            username='docente_test',
            password='test12345',
            rol='DOC',
            first_name='Docente',
            last_name='Prueba',
        )
        self.anio = AnioLectivo.objects.create(anio=2026, activo=True)
        self.grado = Grado.objects.create(nombre='8')
        self.grupo = Grupo.objects.create(nombre='B', grado=self.grado, director_grupo=self.docente)
        self.asignatura = Asignatura.objects.create(nombre='Matematicas', intensidad_horaria=5)

    def test_estudiante_genera_codigo_automatico(self):
        estudiante = Estudiante.objects.create(
            tipo_documento='TI',
            documento='100001',
            nombres='Laura Sofia',
            apellidos='Martinez Torres',
            fecha_nacimiento=date(2011, 5, 12),
            grupo=self.grupo,
            acudiente='Ana Torres',
            telefono_acudiente='3001234567',
        )

        self.assertEqual(estudiante.codigo, 'EST-00001')

    def test_carga_academica_str_incluye_asignatura_grupo_docente(self):
        carga = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )

        self.assertIn('Matematicas', str(carga))
        self.assertIn('8 - B', str(carga))

    def test_listado_estudiantes_filtra_grupos_por_grado(self):
        grado_10 = Grado.objects.create(nombre='10')
        grupo_10a = Grupo.objects.create(nombre='A', grado=grado_10)
        grupo_10b = Grupo.objects.create(nombre='B', grado=grado_10)
        CargaAcademica.objects.create(
            docente=self.docente,
            grupo=grupo_10a,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        CargaAcademica.objects.create(
            docente=self.docente,
            grupo=grupo_10b,
            asignatura=Asignatura.objects.create(nombre='Lengua', intensidad_horaria=4),
            anio_lectivo=self.anio,
        )
        self.client.force_login(self.docente)

        response = self.client.get(f'/academico/estudiantes/?filtrar=1&grado={grado_10.id}')
        grupos = list(response.context['grupos'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(grupo_10a, grupos)
        self.assertIn(grupo_10b, grupos)
        self.assertNotIn(self.grupo, grupos)

    def test_inferir_genero_por_nombre(self):
        self.assertEqual(inferir_genero_por_nombre('Maria Fernanda'), 'F')
        self.assertEqual(inferir_genero_por_nombre('Santiago Jose'), 'M')
        self.assertEqual(inferir_genero_por_nombre('Alex'), 'M')

    def test_horario_no_permite_cruce_docente_ni_grupo(self):
        carga = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
            activo=False,
        )
        horario = HorarioClase.objects.create(
            carga_academica=carga,
            dia_semana=1,
            hora_inicio=time(6, 30),
            hora_fin=time(7, 20),
            aula='Salon 1',
        )

        otra_asignatura = Asignatura.objects.create(nombre='Fisica', intensidad_horaria=2)
        otro_grupo = Grupo.objects.create(nombre='A', grado=Grado.objects.create(nombre='9'))
        carga_mismo_docente = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=otro_grupo,
            asignatura=otra_asignatura,
            anio_lectivo=self.anio,
        )

        with self.assertRaises(ValidationError):
            HorarioClase.objects.create(
                carga_academica=carga_mismo_docente,
                dia_semana=1,
                hora_inicio=horario.hora_inicio,
                hora_fin=horario.hora_fin,
                aula='Salon 2',
            )

    def test_horario_permite_mismo_bloque_en_otro_anio_lectivo(self):
        carga_2026 = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        HorarioClase.objects.create(
            carga_academica=carga_2026,
            dia_semana=1,
            hora_inicio=time(6, 30),
            hora_fin=time(7, 20),
            aula='Salon 1',
        )

        anio_nuevo = AnioLectivo.objects.create(anio=2027, activo=True)
        carga_2027 = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=Asignatura.objects.create(nombre='Biologia', intensidad_horaria=3),
            anio_lectivo=anio_nuevo,
        )

        horario = HorarioClase(
            carga_academica=carga_2027,
            dia_semana=1,
            hora_inicio=time(6, 30),
            hora_fin=time(7, 20),
            aula='Salon 1',
        )
        horario.full_clean()

    def test_horario_no_permite_cruce_aula_en_mismo_anio(self):
        carga_base = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        HorarioClase.objects.create(
            carga_academica=carga_base,
            dia_semana=2,
            hora_inicio=time(7, 20),
            hora_fin=time(8, 10),
            aula='Laboratorio 1',
        )

        otro_docente = get_user_model().objects.create_user(
            username='doc_aula_conflicto',
            password='test12345',
            rol='DOC',
        )
        otro_grupo = Grupo.objects.create(nombre='C', grado=Grado.objects.create(nombre='10'))
        otra_carga = CargaAcademica.objects.create(
            docente=otro_docente,
            grupo=otro_grupo,
            asignatura=Asignatura.objects.create(nombre='Quimica', intensidad_horaria=4),
            anio_lectivo=self.anio,
        )

        with self.assertRaises(ValidationError):
            HorarioClase.objects.create(
                carga_academica=otra_carga,
                dia_semana=2,
                hora_inicio=time(7, 30),
                hora_fin=time(8, 0),
                aula='Laboratorio 1',
            )

    def test_formulario_edicion_muestra_fecha_nacimiento_en_formato_html5(self):
        estudiante = Estudiante.objects.create(
            tipo_documento='TI',
            documento='100009',
            nombres='Carlos Andres',
            apellidos='Rios Lopez',
            fecha_nacimiento=date(2012, 8, 21),
            grupo=self.grupo,
            acudiente='Martha Lopez',
            telefono_acudiente='3009991111',
        )

        form = EstudianteUpdateForm(instance=estudiante)

        self.assertIn('value="2012-08-21"', str(form['fecha_nacimiento']))

    def test_asistencia_no_permite_estudiante_de_otro_grupo(self):
        otro_grado = Grado.objects.create(nombre='9')
        otro_grupo = Grupo.objects.create(nombre='A', grado=otro_grado)
        otro_estudiante = Estudiante.objects.create(
            tipo_documento='TI',
            documento='100010',
            nombres='Luisa Fernanda',
            apellidos='Mendez Ruiz',
            fecha_nacimiento=date(2011, 4, 18),
            grupo=otro_grupo,
            acudiente='Carlos Ruiz',
            telefono_acudiente='3005551111',
        )
        carga = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )

        with self.assertRaises(ValidationError):
            Asistencia.objects.create(
                estudiante=otro_estudiante,
                carga_academica=carga,
                fecha=date(2026, 4, 27),
                estado='P',
            )

    def test_calificacion_no_permite_estudiante_de_otro_grupo(self):
        periodo = PeriodoAcademico.objects.create(
            nombre='Periodo 1',
            numero=1,
            fecha_inicio=date(2026, 1, 27),
            fecha_fin=date(2026, 4, 10),
            anio_lectivo=self.anio,
        )
        otro_grado = Grado.objects.create(nombre='10')
        otro_grupo = Grupo.objects.create(nombre='C', grado=otro_grado)
        otro_estudiante = Estudiante.objects.create(
            tipo_documento='TI',
            documento='100011',
            nombres='Diego Alejandro',
            apellidos='Suarez Lopez',
            fecha_nacimiento=date(2011, 9, 7),
            grupo=otro_grupo,
            acudiente='Lina Lopez',
            telefono_acudiente='3007772222',
        )
        carga = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        actividad = ActividadEvaluativa.objects.create(
            carga_academica=carga,
            periodo=periodo,
            nombre='Quiz 1',
            porcentaje=Decimal('20.00'),
            fecha=date(2026, 3, 3),
        )

        with self.assertRaises(ValidationError):
            Calificacion.objects.create(
                actividad=actividad,
                estudiante=otro_estudiante,
                nota=Decimal('4.00'),
            )


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AcademicoReportesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='coord_reportes',
            password='test12345',
            rol='ADMIN',
        )
        self.anio = AnioLectivo.objects.create(anio=2026, activo=True)
        self.periodo = PeriodoAcademico.objects.create(
            nombre='Primer periodo',
            numero=1,
            fecha_inicio=date(2026, 1, 27),
            fecha_fin=date(2026, 4, 10),
            anio_lectivo=self.anio,
        )
        self.grado = Grado.objects.create(nombre='9')
        self.grupo = Grupo.objects.create(nombre='A', grado=self.grado)
        self.docente = User.objects.create_user(username='doc_reportes', password='test12345', rol='DOC')
        self.asignatura = Asignatura.objects.create(nombre='Lengua Castellana', intensidad_horaria=4)
        self.carga = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        self.estudiante = Estudiante.objects.create(
            tipo_documento='TI',
            documento='20000199',
            nombres='Maria Jose',
            apellidos='Pardo Gomez',
            genero='F',
            fecha_nacimiento=date(2011, 2, 10),
            grupo=self.grupo,
            acudiente='Luisa Gomez',
            correo_acudiente='acudiente@example.com',
            telefono_acudiente='3001234567',
        )
        self.actividad = ActividadEvaluativa.objects.create(
            carga_academica=self.carga,
            periodo=self.periodo,
            nombre='Taller de lectura',
            porcentaje=Decimal('30.00'),
            fecha=date(2026, 4, 9),
            activa=True,
        )
        Calificacion.objects.create(
            actividad=self.actividad,
            estudiante=self.estudiante,
            nota=Decimal('4.20'),
            observacion='Buen desempeño',
        )
        Asistencia.objects.create(
            estudiante=self.estudiante,
            carga_academica=self.carga,
            fecha=date(2026, 4, 10),
            estado='P',
        )
        tipo_alerta = TipoAlerta.objects.create(nombre='Seguimiento academico')
        AlertaTemprana.objects.create(
            estudiante=self.estudiante,
            tipo_alerta=tipo_alerta,
            nivel='ATENCION',
            descripcion='Observacion del periodo.',
            estado='ACTIVA',
        )
        self.client.force_login(self.user)

    def test_reporte_estudiante_renderiza(self):
        response = self.client.get(f'/academico/estudiantes/{self.estudiante.id}/reporte/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.estudiante.apellidos)

    def test_descargar_reporte_estudiante_excel(self):
        response = self.client.get(f'/academico/estudiantes/{self.estudiante.id}/reporte/semanal/descargar/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertTrue(
            ReporteAcudiente.objects.filter(estudiante=self.estudiante, estado='DESCARGADO').exists()
        )

    def test_enviar_reporte_estudiante_por_correo(self):
        response = self.client.get(f'/academico/estudiantes/{self.estudiante.id}/reporte/semanal/enviar/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.estudiante.correo_acudiente, mail.outbox[0].to)
        self.assertTrue(
            ReporteAcudiente.objects.filter(estudiante=self.estudiante, estado='ENVIADO').exists()
        )

    def test_modulo_gestion_reportes_renderiza(self):
        response = self.client.get('/academico/reportes/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Modulo de reportes a acudientes')

    def test_envio_masivo_reportes(self):
        response = self.client.post('/academico/reportes/enviar-masivo/?periodo=semanal')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            ReporteAcudiente.objects.filter(estudiante=self.estudiante, estado='ENVIADO').count(),
            1
        )

    def test_horarios_academicos_renderiza(self):
        HorarioClase.objects.create(
            carga_academica=self.carga,
            dia_semana=1,
            hora_inicio=time(6, 30),
            hora_fin=time(7, 20),
            aula='Salon 10A',
        )

        response = self.client.get('/academico/horarios/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Buscar horarios')
        self.assertContains(response, 'Salon 10A')

    def test_docente_solo_ve_horarios_de_sus_cargas(self):
        otro_docente = get_user_model().objects.create_user(
            username='doc_otro_horario',
            password='test12345',
            rol='DOC',
        )
        otra_asignatura = Asignatura.objects.create(nombre='Matematicas Avanzadas', intensidad_horaria=3)
        otro_grupo = Grupo.objects.create(nombre='B', grado=Grado.objects.create(nombre='11'))
        carga_ajena = CargaAcademica.objects.create(
            docente=otro_docente,
            grupo=otro_grupo,
            asignatura=otra_asignatura,
            anio_lectivo=self.anio,
        )
        HorarioClase.objects.create(
            carga_academica=self.carga,
            dia_semana=1,
            hora_inicio=time(6, 30),
            hora_fin=time(7, 20),
            aula='Salon propio',
        )
        HorarioClase.objects.create(
            carga_academica=carga_ajena,
            dia_semana=1,
            hora_inicio=time(7, 20),
            hora_fin=time(8, 10),
            aula='Salon ajeno',
        )
        self.client.force_login(self.docente)

        response = self.client.get('/academico/horarios/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Salon propio')
        self.assertNotContains(response, 'Salon ajeno')

    def test_horarios_academicos_filtra_por_dia_y_asignatura(self):
        otra_asignatura = Asignatura.objects.create(nombre='Historia', intensidad_horaria=2)
        otra_carga = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=otra_asignatura,
            anio_lectivo=self.anio,
        )
        HorarioClase.objects.create(
            carga_academica=self.carga,
            dia_semana=1,
            hora_inicio=time(6, 30),
            hora_fin=time(7, 20),
            aula='Salon Lengua',
        )
        HorarioClase.objects.create(
            carga_academica=otra_carga,
            dia_semana=2,
            hora_inicio=time(7, 20),
            hora_fin=time(8, 10),
            aula='Salon Historia',
        )

        response = self.client.get(
            f'/academico/horarios/?anio={self.anio.id}&asignatura={self.asignatura.id}&dia=1'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Salon Lengua')
        self.assertNotContains(response, 'Salon Historia')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST='smtp.test.local',
        EMAIL_HOST_USER='test_user',
        EMAIL_HOST_PASSWORD='test_pass',
        DEFAULT_FROM_EMAIL='no-reply@test.local',
    )
    def test_modulo_gestion_reportes_muestra_estado_correo(self):
        response = self.client.get('/academico/reportes/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estado del correo')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST='smtp.test.local',
        EMAIL_HOST_USER='test_user',
        EMAIL_HOST_PASSWORD='test_pass',
        DEFAULT_FROM_EMAIL='no-reply@test.local',
    )
    def test_probar_conexion_correo_redirige_con_mensaje(self):
        response = self.client.post('/academico/reportes/probar-correo/')

        self.assertEqual(response.status_code, 302)

    def test_docente_no_puede_crear_estudiantes(self):
        self.client.force_login(self.docente)

        response = self.client.get('/academico/estudiantes/crear/')

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Acceso denegado', status_code=403)

    def test_docente_no_puede_abrir_reporte_de_estudiante_ajeno(self):
        otro_docente = get_user_model().objects.create_user(
            username='doc_ajeno_reportes',
            password='test12345',
            rol='DOC',
        )
        otro_grado = Grado.objects.create(nombre='11')
        otro_grupo = Grupo.objects.create(nombre='B', grado=otro_grado)
        otro_estudiante = Estudiante.objects.create(
            tipo_documento='TI',
            documento='20000200',
            nombres='Laura Camila',
            apellidos='Vargas Pinto',
            genero='F',
            fecha_nacimiento=date(2011, 6, 15),
            grupo=otro_grupo,
            acudiente='Pedro Vargas',
            correo_acudiente='otroacudiente@example.com',
            telefono_acudiente='3007654321',
        )
        self.client.force_login(otro_docente)

        response = self.client.get(f'/academico/estudiantes/{self.estudiante.id}/reporte/')

        self.assertEqual(response.status_code, 404)

    def test_docente_puede_exportar_estudiantes_visibles(self):
        self.client.force_login(self.docente)

        response = self.client.get('/academico/estudiantes/exportar/excel/?filtrar=1&grado=%s' % self.grado.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_detalle_estudiante_conserva_url_de_retorno(self):
        response = self.client.get(
            f'/academico/estudiantes/{self.estudiante.id}/?next=/academico/estudiantes/%3Ffiltrar%3D1%26grado%3D{self.grado.id}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/academico/estudiantes/?filtrar=1&amp;grado=%s"' % self.grado.id)


class AccesoEstudianteTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.estudiante_user = User.objects.create_user(
            username='est_perm',
            password='test12345',
            rol='EST',
        )
        self.docente = User.objects.create_user(
            username='doc_perm',
            password='test12345',
            rol='DOC',
        )
        self.anio = AnioLectivo.objects.create(anio=2026, activo=True)
        self.periodo = PeriodoAcademico.objects.create(
            nombre='Periodo 1',
            numero=1,
            fecha_inicio=date(2026, 1, 27),
            fecha_fin=date(2026, 4, 10),
            anio_lectivo=self.anio,
        )
        self.grado = Grado.objects.create(nombre='9')
        self.grupo = Grupo.objects.create(nombre='A', grado=self.grado)
        self.asignatura = Asignatura.objects.create(nombre='Matematicas', intensidad_horaria=5)
        self.carga = CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        self.estudiante = Estudiante.objects.create(
            usuario=self.estudiante_user,
            tipo_documento='TI',
            documento='12345678',
            nombres='Laura Sofia',
            apellidos='Martinez Torres',
            fecha_nacimiento=date(2011, 5, 12),
            grupo=self.grupo,
            acudiente='Ana Torres',
            telefono_acudiente='3001234567',
            correo_acudiente='acudiente@example.com',
        )
        self.actividad = ActividadEvaluativa.objects.create(
            carga_academica=self.carga,
            periodo=self.periodo,
            nombre='Parcial 1',
            dimension=ActividadEvaluativa.DIMENSION_PARCIAL,
            porcentaje=Decimal('100.00'),
            fecha=date(2026, 3, 1),
        )

    def test_estudiante_no_puede_registrar_asistencia(self):
        self.client.force_login(self.estudiante_user)

        response = self.client.get(reverse('registrar_asistencia'))

        self.assertEqual(response.status_code, 403)

    def test_estudiante_no_puede_ver_gestion_actividades(self):
        self.client.force_login(self.estudiante_user)

        response = self.client.get(reverse('lista_actividades'))

        self.assertEqual(response.status_code, 403)

    def test_estudiante_no_puede_enviar_reporte(self):
        self.client.force_login(self.estudiante_user)

        response = self.client.get(reverse('enviar_reporte_estudiante', args=[self.estudiante.id, 'semanal']))

        self.assertEqual(response.status_code, 403)
