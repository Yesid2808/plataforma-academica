from academico.models import CargaAcademica, Estudiante, Grupo


def es_docente(user):
    return getattr(user, 'rol', None) == 'DOC'


def es_coordinador(user):
    return getattr(user, 'rol', None) == 'COORD'


def es_admin(user):
    return getattr(user, 'rol', None) == 'ADMIN' or user.is_superuser


def es_estudiante(user):
    return getattr(user, 'rol', None) == 'EST'


def no_es_estudiante(user):
    return not es_estudiante(user)


def puede_ver_todo(user):
    return es_admin(user) or es_coordinador(user)


def puede_gestionar_catalogos(user):
    return puede_ver_todo(user)


def puede_gestionar_docencia(user):
    return es_docente(user) or puede_ver_todo(user)


def obtener_estudiante_usuario(user):
    if not es_estudiante(user):
        return None
    return Estudiante.objects.select_related('grupo', 'grupo__grado').filter(usuario=user).first()


def cargas_visibles_para(user):
    queryset = CargaAcademica.objects.select_related('asignatura', 'grupo', 'grupo__grado').filter(activo=True)

    if es_docente(user) and not puede_ver_todo(user):
        queryset = queryset.filter(docente=user)
    elif es_estudiante(user):
        estudiante = obtener_estudiante_usuario(user)
        queryset = queryset.filter(grupo=estudiante.grupo) if estudiante else queryset.none()

    return queryset


def grupos_visibles_para(user):
    queryset = Grupo.objects.select_related('grado').all().order_by('grado__nombre', 'nombre')

    if es_docente(user) and not puede_ver_todo(user):
        queryset = queryset.filter(cargas_academicas__docente=user, cargas_academicas__activo=True).distinct()
    elif es_estudiante(user):
        estudiante = obtener_estudiante_usuario(user)
        queryset = queryset.filter(pk=estudiante.grupo_id) if estudiante else queryset.none()

    return queryset


def filtrar_estudiantes_visibles(queryset, user):
    if es_docente(user) and not puede_ver_todo(user):
        return queryset.filter(grupo__cargas_academicas__docente=user, grupo__cargas_academicas__activo=True).distinct()
    if es_estudiante(user):
        estudiante = obtener_estudiante_usuario(user)
        return queryset.filter(pk=estudiante.pk) if estudiante else queryset.none()

    return queryset


def filtrar_alertas_visibles(queryset, user):
    if es_docente(user) and not puede_ver_todo(user):
        return queryset.filter(
            estudiante__grupo__cargas_academicas__docente=user,
            estudiante__grupo__cargas_academicas__activo=True,
        ).distinct()
    if es_estudiante(user):
        estudiante = obtener_estudiante_usuario(user)
        return queryset.filter(estudiante=estudiante) if estudiante else queryset.none()

    return queryset
