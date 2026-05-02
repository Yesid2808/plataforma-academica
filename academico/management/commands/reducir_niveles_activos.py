from django.core.management.base import BaseCommand
from django.db import transaction

from academico.models import Asignatura, CargaAcademica, Estudiante, Grado, Grupo, HorarioClase
from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Conserva solo los grados indicados y elimina la informacion academica del resto.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--grados',
            nargs='+',
            default=['6', '7', '8', '9'],
            help='Lista de grados a conservar. Ejemplo: --grados 6 7 8 9',
        )
        parser.add_argument(
            '--solo-preview',
            action='store_true',
            help='Muestra el impacto sin aplicar cambios.',
        )

    def handle(self, *args, **options):
        grados_conservar = sorted({str(grado).strip() for grado in options['grados'] if str(grado).strip()})
        solo_preview = options['solo_preview']

        grupos_conservar = Grupo.objects.filter(grado__nombre__in=grados_conservar)
        grupos_eliminar = Grupo.objects.exclude(grado__nombre__in=grados_conservar)

        estudiantes_eliminar = Estudiante.objects.filter(grupo__in=grupos_eliminar)
        usuarios_estudiante_eliminar_ids = list(
            estudiantes_eliminar.exclude(usuario_id__isnull=True).values_list('usuario_id', flat=True)
        )
        cargas_eliminar = CargaAcademica.objects.filter(grupo__in=grupos_eliminar)
        horarios_eliminar = HorarioClase.objects.filter(carga_academica__in=cargas_eliminar)
        grados_eliminar = Grado.objects.exclude(nombre__in=grados_conservar)

        resumen = {
            'grados_conservar': grados_conservar,
            'grupos_conservar': grupos_conservar.count(),
            'grupos_eliminar': grupos_eliminar.count(),
            'estudiantes_eliminar': estudiantes_eliminar.count(),
            'usuarios_estudiante_eliminar': len(usuarios_estudiante_eliminar_ids),
            'cargas_eliminar': cargas_eliminar.count(),
            'horarios_eliminar': horarios_eliminar.count(),
            'grados_eliminar': grados_eliminar.count(),
        }

        self.stdout.write(self.style.NOTICE('Resumen de reduccion institucional'))
        for clave, valor in resumen.items():
            self.stdout.write(f'- {clave}: {valor}')

        if solo_preview:
            self.stdout.write(self.style.WARNING('No se aplicaron cambios.'))
            return

        with transaction.atomic():
            estudiantes_eliminar.delete()

            if usuarios_estudiante_eliminar_ids:
                Usuario.objects.filter(id__in=usuarios_estudiante_eliminar_ids, rol='EST').delete()

            grupos_eliminar.delete()
            grados_eliminar.delete()

            docentes_sin_uso = Usuario.objects.filter(
                rol='DOC',
                is_superuser=False,
            ).exclude(
                cargas_academicas__activo=True,
            ).exclude(
                grupos_dirigidos__activo=True,
            ).distinct()
            docentes_sin_uso_ids = list(docentes_sin_uso.values_list('id', flat=True))
            total_docentes_sin_uso = len(docentes_sin_uso_ids)
            if docentes_sin_uso_ids:
                Usuario.objects.filter(id__in=docentes_sin_uso_ids).delete()

            asignaturas_sin_uso = Asignatura.objects.exclude(cargas_academicas__activo=True).distinct()
            asignaturas_sin_uso_ids = list(asignaturas_sin_uso.values_list('id', flat=True))
            total_asignaturas_sin_uso = len(asignaturas_sin_uso_ids)
            if asignaturas_sin_uso_ids:
                Asignatura.objects.filter(id__in=asignaturas_sin_uso_ids).delete()

        self.stdout.write(self.style.SUCCESS('Reduccion completada correctamente.'))
        self.stdout.write(f'- Docentes eliminados sin cargas restantes: {total_docentes_sin_uso}')
        self.stdout.write(f'- Asignaturas eliminadas sin cargas restantes: {total_asignaturas_sin_uso}')
        self.stdout.write(f'- Grupos activos restantes: {Grupo.objects.filter(activo=True).count()}')
        self.stdout.write(f'- Estudiantes activos restantes: {Estudiante.objects.filter(activo=True).count()}')
        self.stdout.write(f'- Cargas activas restantes: {CargaAcademica.objects.filter(activo=True).count()}')
        self.stdout.write(f'- Horarios restantes: {HorarioClase.objects.count()}')
