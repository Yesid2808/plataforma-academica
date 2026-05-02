from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from academico.models import AnioLectivo, Asignatura, CargaAcademica, Estudiante, Grado, Grupo
from usuarios.models import NotificacionUsuario
from usuarios.permissions import cargas_visibles_para, puede_ver_todo


class PermisosRolTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin_test', password='test12345', rol='ADMIN')
        self.docente = User.objects.create_user(username='doc_test', password='test12345', rol='DOC')
        self.otro_docente = User.objects.create_user(username='otro_doc_test', password='test12345', rol='DOC')
        self.anio = AnioLectivo.objects.create(anio=2026)
        self.grado = Grado.objects.create(nombre='8')
        self.grupo = Grupo.objects.create(nombre='B', grado=self.grado)
        self.asignatura = Asignatura.objects.create(nombre='Matematicas')
        self.otra_asignatura = Asignatura.objects.create(nombre='Ciencias')
        CargaAcademica.objects.create(
            docente=self.docente,
            grupo=self.grupo,
            asignatura=self.asignatura,
            anio_lectivo=self.anio,
        )
        CargaAcademica.objects.create(
            docente=self.otro_docente,
            grupo=self.grupo,
            asignatura=self.otra_asignatura,
            anio_lectivo=self.anio,
        )

    def test_admin_puede_ver_todo(self):
        self.assertTrue(puede_ver_todo(self.admin))
        self.assertEqual(cargas_visibles_para(self.admin).count(), 2)

    def test_docente_solo_ve_sus_cargas(self):
        self.assertFalse(puede_ver_todo(self.docente))
        cargas = cargas_visibles_para(self.docente)
        self.assertEqual(cargas.count(), 1)
        self.assertEqual(cargas.first().docente, self.docente)

    def test_base_muestra_nombre_sesion(self):
        self.admin.first_name = 'Ana'
        self.admin.last_name = 'Torres'
        self.admin.save()
        self.client.force_login(self.admin)

        response = self.client.get(reverse('inicio'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana Torres')

    def test_usuario_puede_ver_notificaciones(self):
        NotificacionUsuario.objects.create(
            usuario=self.admin,
            actor=self.docente,
            tipo='SISTEMA',
            titulo='Prueba',
            mensaje='Notificacion de prueba',
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('lista_notificaciones'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Notificacion de prueba')

    def test_estudiante_no_ve_modulos_desactivados_en_menu_ni_campana(self):
        estudiante_user = get_user_model().objects.create_user(
            username='est_test_menu',
            password='test12345',
            rol='EST',
        )
        Estudiante.objects.create(
            tipo_documento='TI',
            documento='900001',
            nombres='Laura Sofia',
            apellidos='Rios Perez',
            fecha_nacimiento=date(2012, 2, 14),
            grupo=self.grupo,
            usuario=estudiante_user,
            acudiente='Ana Perez',
            telefono_acudiente='3000001111',
        )
        self.client.force_login(estudiante_user)

        response = self.client.get(reverse('inicio'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Notificaciones')
        self.assertNotContains(response, 'Asistencias')
        self.assertNotContains(response, 'Calificaciones')
        self.assertNotContains(response, 'bi-bell-fill')

    def test_estudiante_no_puede_abrir_modulos_desactivados_por_url(self):
        estudiante_user = get_user_model().objects.create_user(
            username='est_test_bloqueo',
            password='test12345',
            rol='EST',
        )
        Estudiante.objects.create(
            tipo_documento='TI',
            documento='900002',
            nombres='Carlos Andres',
            apellidos='Mora Diaz',
            fecha_nacimiento=date(2011, 9, 7),
            grupo=self.grupo,
            usuario=estudiante_user,
            acudiente='Lina Diaz',
            telefono_acudiente='3000002222',
        )
        self.client.force_login(estudiante_user)

        self.assertEqual(self.client.get(reverse('lista_notificaciones')).status_code, 403)
        self.assertEqual(self.client.get(reverse('resumen_asistencia')).status_code, 403)
        self.assertEqual(self.client.get(reverse('resumen_calificaciones')).status_code, 403)


class LoginSeguridadTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.usuario = User.objects.create_user(
            username='seguridad_test',
            password='Segura12345',
            rol='ADMIN',
        )

    @override_settings(LOGIN_MAX_ATTEMPTS=2, LOGIN_LOCK_MINUTES=5)
    def test_login_se_bloquea_tras_intentos_fallidos(self):
        url = reverse('login')

        respuesta_1 = self.client.post(url, {
            'username': self.usuario.username,
            'password': 'incorrecta-1',
        })
        self.assertContains(respuesta_1, 'Intentos restantes: 1')

        respuesta_2 = self.client.post(url, {
            'username': self.usuario.username,
            'password': 'incorrecta-2',
        })
        self.assertContains(respuesta_2, 'Se bloqueo temporalmente el acceso')

        respuesta_3 = self.client.post(url, {
            'username': self.usuario.username,
            'password': 'Segura12345',
        })
        self.assertContains(respuesta_3, 'Inicio de sesion bloqueado temporalmente')

    def test_vista_protegida_redirige_a_login_si_no_hay_sesion(self):
        respuesta = self.client.get('/academico/estudiantes/crear/')

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/usuarios/login/', respuesta.url)
