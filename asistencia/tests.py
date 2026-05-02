from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from academico.models import AnioLectivo, Asignatura, CargaAcademica, Estudiante, Grado, Grupo
from asistencia.models import Asistencia
from usuarios.models import NotificacionUsuario


class AsistenciaPermisosTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.docente = User.objects.create_user(username='doc_asis', password='test12345', rol='DOC')
        self.otro_docente = User.objects.create_user(username='otro_doc_asis', password='test12345', rol='DOC')
        self.anio = AnioLectivo.objects.create(anio=2026)
        self.grado = Grado.objects.create(nombre='10')
        self.grupo = Grupo.objects.create(nombre='A', grado=self.grado)
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
        self.coordinador = User.objects.create_user(username='coord_asis', password='test12345', rol='COORD')
        self.estudiante = Estudiante.objects.create(
            tipo_documento='TI',
            documento='800001',
            nombres='Carlos',
            apellidos='Mora',
            fecha_nacimiento=date(2011, 5, 1),
            grupo=self.grupo,
            acudiente='Maria Mora',
            telefono_acudiente='3001112233',
        )

    def test_formulario_muestra_solo_cargas_del_docente(self):
        self.client.force_login(self.docente)
        response = self.client.get(reverse('registrar_asistencia'))

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn(self.carga, list(form.fields['carga_academica'].queryset))
        self.assertNotIn(self.carga_ajena, list(form.fields['carga_academica'].queryset))

    def test_resumen_filtra_grupos_por_grado(self):
        grado_11 = Grado.objects.create(nombre='11')
        grupo_11a = Grupo.objects.create(nombre='A', grado=grado_11)
        CargaAcademica.objects.create(
            docente=self.docente,
            grupo=grupo_11a,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        self.client.force_login(self.docente)

        response = self.client.get(f"{reverse('resumen_asistencia')}?grado={grado_11.id}")
        grupos = list(response.context['grupos'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(grupo_11a, grupos)
        self.assertNotIn(self.grupo, grupos)

    def test_exportar_resumen_asistencia_excel(self):
        self.client.force_login(self.docente)

        response = self.client.get(reverse('exportar_resumen_asistencia_excel'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_modificar_asistencia_docente_genera_notificacion(self):
        Asistencia.objects.create(
            estudiante=self.estudiante,
            carga_academica=self.carga,
            fecha=date.today(),
            estado='P',
        )
        self.client.force_login(self.docente)

        response = self.client.post(reverse('registrar_asistencia'), {
            'modificar': '1',
            'carga_academica': self.carga.id,
            f'estado_{self.estudiante.id}': 'A',
            f'observacion_{self.estudiante.id}': 'Cambio manual',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            NotificacionUsuario.objects.filter(
                usuario=self.coordinador,
                tipo='ASISTENCIA',
            ).exists()
        )
        self.assertTrue(
            NotificacionUsuario.objects.filter(
                usuario=self.docente,
                tipo='ASISTENCIA',
            ).exists()
        )
