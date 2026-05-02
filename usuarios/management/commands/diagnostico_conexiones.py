from urllib.parse import urlparse

from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = 'Verifica las conexiones principales del proyecto: PostgreSQL, SMTP y Power BI.'

    def handle(self, *args, **options):
        resultados = [
            self._verificar_base_datos(),
            self._verificar_correo(),
            self._verificar_powerbi(),
        ]

        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Resumen de conexiones'))
        self.stdout.write('-' * 60)

        exitosas = 0
        for resultado in resultados:
            estilo = self.style.SUCCESS if resultado['ok'] else self.style.ERROR
            estado = 'OK' if resultado['ok'] else 'ERROR'
            self.stdout.write(estilo(f"[{estado}] {resultado['nombre']}"))
            self.stdout.write(f"  Detalle: {resultado['detalle']}")
            if resultado.get('recomendacion'):
                self.stdout.write(f"  Recomendacion: {resultado['recomendacion']}")
            self.stdout.write('')
            exitosas += int(resultado['ok'])

        if exitosas == len(resultados):
            self.stdout.write(self.style.SUCCESS('Todas las conexiones principales estan listas.'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Se validaron {len(resultados)} conexiones y {len(resultados) - exitosas} requieren ajuste.'
                )
            )

    def _verificar_base_datos(self):
        configuracion = settings.DATABASES['default']
        alias = 'default'
        host = configuracion.get('HOST') or 'localhost'
        port = configuracion.get('PORT') or '5432'
        base = configuracion.get('NAME') or ''

        try:
            with connections[alias].cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            return {
                'nombre': 'Base de datos PostgreSQL',
                'ok': True,
                'detalle': f'Conexion exitosa a {base} en {host}:{port}.',
            }
        except Exception as exc:
            return {
                'nombre': 'Base de datos PostgreSQL',
                'ok': False,
                'detalle': f'No fue posible conectar a {base} en {host}:{port}. Error: {exc}',
                'recomendacion': 'Verifica que el servicio PostgreSQL local este iniciado y que el puerto configurado sea el correcto.',
            }

    def _verificar_correo(self):
        backend = getattr(settings, 'EMAIL_BACKEND', '')
        if backend == 'django.core.mail.backends.console.EmailBackend':
            return {
                'nombre': 'Correo SMTP',
                'ok': False,
                'detalle': 'El backend actual es de consola; los correos no se envian realmente.',
                'recomendacion': 'Configura EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD y DEFAULT_FROM_EMAIL en el archivo .env.',
            }

        faltantes = [
            campo for campo, valor in {
                'EMAIL_HOST': settings.EMAIL_HOST,
                'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
                'EMAIL_HOST_PASSWORD': settings.EMAIL_HOST_PASSWORD,
                'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
            }.items() if not valor
        ]

        if faltantes:
            return {
                'nombre': 'Correo SMTP',
                'ok': False,
                'detalle': f'Faltan variables obligatorias: {", ".join(faltantes)}.',
                'recomendacion': 'Completa la configuracion SMTP antes de intentar envios reales.',
            }

        connection = get_connection()
        try:
            opened = connection.open()
            if opened is False:
                raise RuntimeError('El servidor SMTP rechazo la apertura de la conexion.')
            return {
                'nombre': 'Correo SMTP',
                'ok': True,
                'detalle': f'Conexion SMTP validada con backend {backend}.',
            }
        except Exception as exc:
            return {
                'nombre': 'Correo SMTP',
                'ok': False,
                'detalle': f'La conexion SMTP fallo: {exc}',
                'recomendacion': 'Confirma host, puerto, TLS y credenciales de la cuenta de correo.',
            }
        finally:
            connection.close()

    def _verificar_powerbi(self):
        url = getattr(settings, 'POWERBI_DASHBOARD_URL', '').strip()
        if not url:
            return {
                'nombre': 'Power BI embebido',
                'ok': False,
                'detalle': 'No hay URL configurada para el tablero embebido.',
                'recomendacion': 'Define POWERBI_DASHBOARD_URL en .env con la URL de insercion del reporte publicado.',
            }

        parsed = urlparse(url)
        dominio = parsed.netloc.lower()
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            return {
                'nombre': 'Power BI embebido',
                'ok': False,
                'detalle': 'La URL configurada no tiene un formato valido.',
                'recomendacion': 'Usa una URL completa que empiece por https://',
            }

        if 'powerbi' not in dominio:
            return {
                'nombre': 'Power BI embebido',
                'ok': False,
                'detalle': f'La URL apunta a un dominio inesperado: {parsed.netloc}',
                'recomendacion': 'Revisa que sea una URL de Power BI Share o Embed.',
            }

        return {
            'nombre': 'Power BI embebido',
            'ok': True,
            'detalle': f'URL de Power BI configurada correctamente para {parsed.netloc}.',
        }
