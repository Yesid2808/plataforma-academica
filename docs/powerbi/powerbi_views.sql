-- Vistas analiticas para Power BI.
-- Ejecutar en PostgreSQL sobre la base plataforma_academica_v2.
-- Las vistas no reemplazan tablas transaccionales; solo preparan datos de lectura.

CREATE OR REPLACE VIEW public.powerbi_dim_estudiante AS
SELECT
    e.id AS estudiante_id,
    e.codigo,
    e.documento,
    e.nombres,
    e.apellidos,
    CONCAT(e.apellidos, ' ', e.nombres) AS estudiante,
    e.genero,
    e.fecha_nacimiento,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.fecha_nacimiento))::int AS edad,
    e.activo AS estudiante_activo,
    e.fecha_registro::date AS fecha_registro,
    e.grupo_id,
    g.nombre AS grupo,
    gr.id AS grado_id,
    gr.nombre AS grado,
    e.acudiente,
    e.telefono_acudiente,
    e.correo_acudiente,
    e.whatsapp_acudiente
FROM public.academico_estudiante e
JOIN public.academico_grupo g ON g.id = e.grupo_id
JOIN public.academico_grado gr ON gr.id = g.grado_id;


CREATE OR REPLACE VIEW public.powerbi_dim_carga_academica AS
SELECT
    ca.id AS carga_academica_id,
    ca.activo AS carga_activa,
    ca.grupo_id,
    g.nombre AS grupo,
    gr.id AS grado_id,
    gr.nombre AS grado,
    ca.asignatura_id,
    a.nombre AS asignatura,
    a.intensidad_horaria,
    ca.anio_lectivo_id,
    al.anio AS anio_lectivo,
    ca.docente_id,
    u.username AS docente_usuario,
    TRIM(CONCAT(COALESCE(u.first_name, ''), ' ', COALESCE(u.last_name, ''))) AS docente_nombre
FROM public.academico_cargaacademica ca
JOIN public.academico_grupo g ON g.id = ca.grupo_id
JOIN public.academico_grado gr ON gr.id = g.grado_id
JOIN public.academico_asignatura a ON a.id = ca.asignatura_id
JOIN public.academico_aniolectivo al ON al.id = ca.anio_lectivo_id
JOIN public.usuarios_usuario u ON u.id = ca.docente_id;


CREATE OR REPLACE VIEW public.powerbi_dim_periodo AS
SELECT
    p.id AS periodo_id,
    p.nombre AS periodo,
    p.numero AS periodo_numero,
    p.fecha_inicio,
    p.fecha_fin,
    p.activo AS periodo_activo,
    p.anio_lectivo_id,
    al.anio AS anio_lectivo
FROM public.academico_periodoacademico p
JOIN public.academico_aniolectivo al ON al.id = p.anio_lectivo_id;


CREATE OR REPLACE VIEW public.powerbi_fact_asistencia AS
SELECT
    asi.id AS asistencia_id,
    asi.fecha,
    asi.fecha_registro::date AS fecha_registro,
    asi.estudiante_id,
    asi.carga_academica_id,
    asi.estado,
    CASE asi.estado
        WHEN 'P' THEN 'Presente'
        WHEN 'A' THEN 'Ausente'
        WHEN 'T' THEN 'Tarde'
        WHEN 'J' THEN 'Justificado'
        ELSE 'Sin clasificar'
    END AS estado_asistencia,
    CASE WHEN asi.estado = 'P' THEN 1 ELSE 0 END AS presente,
    CASE WHEN asi.estado = 'A' THEN 1 ELSE 0 END AS ausente,
    CASE WHEN asi.estado = 'T' THEN 1 ELSE 0 END AS tarde,
    CASE WHEN asi.estado = 'J' THEN 1 ELSE 0 END AS justificado,
    asi.observacion
FROM public.asistencia_asistencia asi;


CREATE OR REPLACE VIEW public.powerbi_fact_actividad_evaluativa AS
SELECT
    act.id AS actividad_id,
    act.nombre AS actividad,
    act.carga_academica_id,
    act.periodo_id,
    act.fecha,
    act.porcentaje,
    act.activa AS actividad_activa
FROM public.evaluacion_actividadevaluativa act;


CREATE OR REPLACE VIEW public.powerbi_fact_calificacion AS
SELECT
    cal.id AS calificacion_id,
    cal.estudiante_id,
    cal.actividad_id,
    act.carga_academica_id,
    act.periodo_id,
    act.fecha AS fecha_actividad,
    cal.fecha_registro::date AS fecha_registro,
    cal.nota,
    act.porcentaje,
    ROUND((cal.nota * act.porcentaje / 100.0)::numeric, 2) AS aporte_ponderado,
    CASE
        WHEN cal.nota < 3.0 THEN 'Bajo'
        WHEN cal.nota < 4.0 THEN 'Basico'
        WHEN cal.nota < 4.6 THEN 'Alto'
        ELSE 'Superior'
    END AS desempeno_escala_1290,
    CASE WHEN cal.nota < 3.0 THEN 1 ELSE 0 END AS bajo_desempeno,
    cal.observacion
FROM public.evaluacion_calificacion cal
JOIN public.evaluacion_actividadevaluativa act ON act.id = cal.actividad_id;


CREATE OR REPLACE VIEW public.powerbi_fact_alerta AS
SELECT
    al.id AS alerta_id,
    al.estudiante_id,
    al.tipo_alerta_id,
    ta.nombre AS tipo_alerta,
    al.configuracion_id,
    ca.nombre AS configuracion_alerta,
    al.nivel,
    al.estado,
    al.fecha_generacion,
    al.fecha_generacion::date AS fecha_alerta,
    al.descripcion,
    CASE WHEN al.estado = 'ACTIVA' THEN 1 ELSE 0 END AS alerta_activa,
    CASE WHEN al.nivel = 'CRITICO' AND al.estado = 'ACTIVA' THEN 1 ELSE 0 END AS alerta_critica_activa
FROM public.alertas_alertatemprana al
LEFT JOIN public.alertas_tipoalerta ta ON ta.id = al.tipo_alerta_id
LEFT JOIN public.alertas_configuracionalerta ca ON ca.id = al.configuracion_id;


CREATE OR REPLACE VIEW public.powerbi_fact_seguimiento_alerta AS
SELECT
    seg.id AS seguimiento_id,
    seg.alerta_id,
    al.estudiante_id,
    al.tipo_alerta_id,
    ta.nombre AS tipo_alerta,
    al.nivel AS nivel_alerta,
    al.estado AS estado_alerta,
    seg.registrado_por_id,
    u.username AS registrado_por_usuario,
    TRIM(CONCAT(COALESCE(u.first_name, ''), ' ', COALESCE(u.last_name, ''))) AS registrado_por_nombre,
    seg.accion,
    CASE seg.accion
        WHEN 'CONTACTO_ACUDIENTE' THEN 'Contacto con acudiente'
        WHEN 'APOYO_PEDAGOGICO' THEN 'Apoyo pedagogico'
        WHEN 'REMISION_ORIENTACION' THEN 'Remision a orientacion'
        WHEN 'COMPROMISO_ACADEMICO' THEN 'Compromiso academico'
        WHEN 'OBSERVACION' THEN 'Observacion'
        ELSE 'Sin clasificar'
    END AS accion_seguimiento,
    seg.resultado,
    CASE seg.resultado
        WHEN 'PENDIENTE' THEN 'Pendiente'
        WHEN 'EN_PROCESO' THEN 'En proceso'
        WHEN 'MEJORA' THEN 'Presenta mejora'
        WHEN 'SIN_MEJORA' THEN 'Sin mejora'
        WHEN 'CERRADO' THEN 'Caso cerrado'
        ELSE 'Sin clasificar'
    END AS resultado_seguimiento,
    seg.fecha_registro,
    seg.fecha_registro::date AS fecha_seguimiento,
    seg.proxima_revision,
    CASE WHEN seg.proxima_revision IS NOT NULL AND seg.proxima_revision < CURRENT_DATE THEN 1 ELSE 0 END AS revision_vencida,
    seg.descripcion
FROM public.alertas_seguimientoalerta seg
JOIN public.alertas_alertatemprana al ON al.id = seg.alerta_id
LEFT JOIN public.alertas_tipoalerta ta ON ta.id = al.tipo_alerta_id
LEFT JOIN public.usuarios_usuario u ON u.id = seg.registrado_por_id;


CREATE OR REPLACE VIEW public.powerbi_mart_seguimiento_estudiante AS
SELECT
    e.estudiante_id,
    e.codigo,
    e.estudiante,
    e.grupo_id,
    e.grupo,
    e.grado_id,
    e.grado,
    COUNT(seg.seguimiento_id) AS total_seguimientos,
    COUNT(DISTINCT seg.alerta_id) AS alertas_con_seguimiento,
    COUNT(seg.seguimiento_id) FILTER (WHERE seg.resultado = 'MEJORA') AS seguimientos_con_mejora,
    COUNT(seg.seguimiento_id) FILTER (WHERE seg.resultado = 'CERRADO') AS seguimientos_cerrados,
    COUNT(seg.seguimiento_id) FILTER (WHERE seg.revision_vencida = 1) AS revisiones_vencidas,
    MAX(seg.fecha_seguimiento) AS ultimo_seguimiento
FROM public.powerbi_dim_estudiante e
LEFT JOIN public.powerbi_fact_seguimiento_alerta seg ON seg.estudiante_id = e.estudiante_id
WHERE e.estudiante_activo = true
GROUP BY
    e.estudiante_id,
    e.codigo,
    e.estudiante,
    e.grupo_id,
    e.grupo,
    e.grado_id,
    e.grado;


CREATE OR REPLACE VIEW public.powerbi_mart_riesgo_estudiante AS
WITH calificaciones AS (
    SELECT
        cal.estudiante_id,
        COUNT(cal.id) AS total_calificaciones,
        ROUND(AVG(cal.nota)::numeric, 2) AS promedio_simple,
        ROUND(
            CASE
                WHEN SUM(act.porcentaje) > 0 THEN SUM(cal.nota * act.porcentaje) / SUM(act.porcentaje)
                ELSE NULL
            END::numeric,
            2
        ) AS promedio_ponderado,
        SUM(CASE WHEN cal.nota < 3.0 THEN 1 ELSE 0 END) AS actividades_bajo_desempeno
    FROM public.evaluacion_calificacion cal
    JOIN public.evaluacion_actividadevaluativa act ON act.id = cal.actividad_id
    GROUP BY cal.estudiante_id
),
asistencias AS (
    SELECT
        estudiante_id,
        COUNT(*) AS total_registros_asistencia,
        SUM(CASE WHEN estado = 'P' THEN 1 ELSE 0 END) AS total_presentes,
        SUM(CASE WHEN estado = 'A' THEN 1 ELSE 0 END) AS total_ausentes,
        SUM(CASE WHEN estado = 'T' THEN 1 ELSE 0 END) AS total_tardes,
        SUM(CASE WHEN estado = 'J' THEN 1 ELSE 0 END) AS total_justificados,
        ROUND(
            CASE
                WHEN COUNT(*) > 0 THEN SUM(CASE WHEN estado = 'P' THEN 1 ELSE 0 END)::numeric * 100 / COUNT(*)
                ELSE 0
            END,
            2
        ) AS porcentaje_asistencia
    FROM public.asistencia_asistencia
    GROUP BY estudiante_id
),
alertas AS (
    SELECT
        estudiante_id,
        COUNT(*) FILTER (WHERE estado = 'ACTIVA') AS alertas_activas,
        COUNT(*) FILTER (WHERE estado = 'ACTIVA' AND nivel = 'CRITICO') AS alertas_criticas_activas
    FROM public.alertas_alertatemprana
    GROUP BY estudiante_id
),
seguimientos AS (
    SELECT
        al.estudiante_id,
        COUNT(seg.id) AS total_seguimientos,
        COUNT(seg.id) FILTER (WHERE seg.resultado = 'MEJORA') AS seguimientos_con_mejora,
        COUNT(seg.id) FILTER (WHERE seg.resultado = 'CERRADO') AS seguimientos_cerrados,
        COUNT(seg.id) FILTER (
            WHERE seg.proxima_revision IS NOT NULL
              AND seg.proxima_revision < CURRENT_DATE
        ) AS revisiones_vencidas,
        MAX(seg.fecha_registro)::date AS ultimo_seguimiento
    FROM public.alertas_seguimientoalerta seg
    JOIN public.alertas_alertatemprana al ON al.id = seg.alerta_id
    GROUP BY al.estudiante_id
)
SELECT
    e.estudiante_id,
    e.codigo,
    e.estudiante,
    e.grupo_id,
    e.grupo,
    e.grado_id,
    e.grado,
    COALESCE(c.total_calificaciones, 0) AS total_calificaciones,
    c.promedio_simple,
    c.promedio_ponderado,
    COALESCE(c.actividades_bajo_desempeno, 0) AS actividades_bajo_desempeno,
    COALESCE(a.total_registros_asistencia, 0) AS total_registros_asistencia,
    COALESCE(a.total_presentes, 0) AS total_presentes,
    COALESCE(a.total_ausentes, 0) AS total_ausentes,
    COALESCE(a.total_tardes, 0) AS total_tardes,
    COALESCE(a.total_justificados, 0) AS total_justificados,
    COALESCE(a.porcentaje_asistencia, 0) AS porcentaje_asistencia,
    COALESCE(al.alertas_activas, 0) AS alertas_activas,
    COALESCE(al.alertas_criticas_activas, 0) AS alertas_criticas_activas,
    COALESCE(s.total_seguimientos, 0) AS total_seguimientos,
    COALESCE(s.seguimientos_con_mejora, 0) AS seguimientos_con_mejora,
    COALESCE(s.seguimientos_cerrados, 0) AS seguimientos_cerrados,
    COALESCE(s.revisiones_vencidas, 0) AS revisiones_vencidas,
    s.ultimo_seguimiento,
    CASE
        WHEN COALESCE(c.promedio_ponderado, c.promedio_simple, 5) < 3.0
             AND COALESCE(a.total_ausentes, 0) >= 3 THEN 'CRITICO'
        WHEN COALESCE(c.promedio_ponderado, c.promedio_simple, 5) < 3.0
             OR COALESCE(a.total_ausentes, 0) >= 3 THEN 'RIESGO'
        WHEN COALESCE(c.actividades_bajo_desempeno, 0) > 0
             OR COALESCE(a.total_ausentes, 0) = 2 THEN 'ATENCION'
        ELSE 'NORMAL'
    END AS nivel_riesgo_integral
FROM public.powerbi_dim_estudiante e
LEFT JOIN calificaciones c ON c.estudiante_id = e.estudiante_id
LEFT JOIN asistencias a ON a.estudiante_id = e.estudiante_id
LEFT JOIN alertas al ON al.estudiante_id = e.estudiante_id
LEFT JOIN seguimientos s ON s.estudiante_id = e.estudiante_id
WHERE e.estudiante_activo = true;
