# Analisis tecnico de la aplicacion

Proyecto: Plataforma academica con analitica de datos y alertas tempranas.

## Configuracion

- `config/settings.py`: centraliza apps instaladas, conexion PostgreSQL, zona horaria, archivos estaticos/media y autenticacion. Se agrego `POWERBI_DASHBOARD_URL` para insertar el reporte de Power BI desde `.env`.
- `config/urls.py`: concentra rutas globales y conecta `dashboard`, `usuarios`, `academico`, `asistencia`, `alertas` y `evaluacion`.
- `config/pg_connection_check.py`: reemplaza al archivo `test_pg.py` para evitar que Django lo ejecute accidentalmente durante `manage.py test`.

## Usuarios

- `usuarios/models.py`: define el usuario personalizado con roles `ADMIN`, `COORD` y `DOC`.
- `usuarios/admin.py`: expone rol y telefono en Django admin.
- `usuarios/views.py`: controla login y logout.
- `usuarios/urls.py`: publica rutas de autenticacion.

Mejora pendiente recomendada: aplicar permisos por rol en vistas sensibles, especialmente calificaciones, asistencia y alertas.

## Academico

- `academico/models.py`: contiene ano lectivo, periodos, grados, grupos, asignaturas, estudiantes y cargas academicas. Se elimino duplicacion interna en `Estudiante`.
- `academico/forms.py`: formularios de estudiantes e importacion Excel.
- `academico/views.py`: CRUD de estudiantes, exportacion/importacion Excel y detalle.
- `academico/urls.py`: rutas de estudiantes.
- `academico/admin.py`: administracion de entidades academicas.
- `academico/management/commands/seed_demo_data.py`: comando reproducible para crear datos institucionales demo.

Mejora pendiente recomendada: agregar CRUD propio para grados, grupos, asignaturas y cargas academicas fuera del admin.

## Asistencia

- `asistencia/models.py`: registro unico por estudiante, carga academica y fecha.
- `asistencia/forms.py`: selector de carga academica.
- `asistencia/views.py`: registro masivo de asistencia, historial y resumen.
- `asistencia/urls.py`: rutas de registro y resumen.
- `asistencia/admin.py`: administracion de registros.

Mejora pendiente recomendada: permitir seleccionar fecha controlada por rol o calendario academico, no solo fecha actual.

## Evaluacion

- `evaluacion/models.py`: actividades evaluativas y calificaciones con validacion de notas.
- `evaluacion/forms.py`: formulario de actividad evaluativa.
- `evaluacion/views.py`: listado, creacion, edicion, eliminacion, registro masivo de calificaciones y resumen.
- `evaluacion/urls.py`: rutas funcionales del modulo.
- `templates/evaluacion/`: pantallas del modulo de calificaciones.

Mejora pendiente recomendada: generar alertas de bajo rendimiento automaticamente al guardar calificaciones, no solo desde datos demo.

## Alertas

- `alertas/models.py`: tipos de alerta, configuraciones y alertas tempranas.
- `alertas/utils.py`: evaluacion de alerta por inasistencia acumulada.
- `alertas/views.py`: consulta y gestion de alertas.
- `alertas/urls.py`: rutas de alertas.
- `alertas/admin.py`: administracion de reglas y alertas.

Mejora pendiente recomendada: extender `utils.py` con reglas de bajo rendimiento academico y riesgo integral.

## Dashboard

- `dashboard/views.py`: indicadores institucionales de asistencia, alertas y bajo desempeno.
- `templates/dashboard/inicio.html`: visuales internos con Chart.js y bloque para insertar Power BI.

Mejora pendiente recomendada: configurar `POWERBI_DASHBOARD_URL` con la URL de insercion del reporte publicado en Power BI.

## Power BI

- `docs/powerbi/powerbi_views.sql`: vistas analiticas para Power BI.
- `docs/powerbi/README.md`: guia de conexion, modelo de relaciones, medidas DAX y paginas recomendadas.

Vistas validadas:

- `powerbi_dim_estudiante`
- `powerbi_dim_carga_academica`
- `powerbi_dim_periodo`
- `powerbi_fact_asistencia`
- `powerbi_fact_actividad_evaluativa`
- `powerbi_fact_calificacion`
- `powerbi_fact_alerta`
- `powerbi_mart_riesgo_estudiante`

## Datos demo generados

Grupos agregados o completados:

- `8 - B`
- `10 - A`
- `10 - B`

Cada grupo quedo con maximo 30 estudiantes activos. Tambien se generaron cargas academicas, actividades evaluativas, calificaciones, asistencias y alertas tempranas para alimentar el dashboard y Power BI.
