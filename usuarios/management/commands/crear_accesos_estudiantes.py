from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from academico.models import Estudiante


class Command(BaseCommand):
    help = 'Crea accesos para estudiantes activos que aun no tengan usuario asociado.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password-base',
            default='Estu@',
            help='Prefijo de la contrasena temporal. Se complementa con los ultimos 4 digitos del documento.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        password_base = options['password_base']
        creados = 0
        actualizados = 0
        omitidos = 0

        estudiantes = Estudiante.objects.select_related('usuario').filter(activo=True).order_by('apellidos', 'nombres')

        for estudiante in estudiantes:
            if estudiante.usuario_id:
                omitidos += 1
                continue

            documento = ''.join(ch for ch in str(estudiante.documento or '') if ch.isdigit())
            if not documento:
                omitidos += 1
                continue

            username = documento
            if User.objects.filter(username=username).exclude(pk=getattr(estudiante.usuario, 'pk', None)).exists():
                username = f'est_{documento}'
                if User.objects.filter(username=username).exists():
                    omitidos += 1
                    continue

            password_temporal = f"{password_base}{documento[-4:]}"
            user = User.objects.filter(username=username).first()

            if user:
                user.rol = 'EST'
                user.first_name = estudiante.nombres[:150]
                user.last_name = estudiante.apellidos[:150]
                user.email = estudiante.correo or ''
                user.set_password(password_temporal)
                user.save(update_fields=['rol', 'first_name', 'last_name', 'email', 'password'])
                actualizados += 1
            else:
                user = User.objects.create_user(
                    username=username,
                    password=password_temporal,
                    rol='EST',
                    first_name=estudiante.nombres[:150],
                    last_name=estudiante.apellidos[:150],
                    email=estudiante.correo or '',
                )
                creados += 1

            estudiante.usuario = user
            estudiante.save(update_fields=['usuario'])

            self.stdout.write(
                f'{estudiante.codigo} | {estudiante.apellidos} {estudiante.nombres} | usuario: {username} | clave temporal: {password_temporal}'
            )

        self.stdout.write(self.style.SUCCESS(
            f'Proceso completado. Creados: {creados}, actualizados: {actualizados}, omitidos: {omitidos}.'
        ))
