from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Crea vistas SQL en PostgreSQL para consumir alertas y riesgo "
        "estudiantil desde Power BI."
    )

    VIEW_SQL = {
        "vw_powerbi_alertas_detalle": """
            CREATE OR REPLACE VIEW vw_powerbi_alertas_detalle AS
            SELECT
                a.id AS alerta_id,
                a.estudiante_id,
                e.codigo AS estudiante_codigo,
                e.documento AS estudiante_documento,
                e.apellidos || ' ' || e.nombres AS estudiante_nombre,
                g.nombre AS grupo_nombre,
                gr.nombre AS grado_nombre,
                gr.nombre || g.nombre AS grado_grupo,
                ta.nombre AS tipo_alerta,
                ta.descripcion AS tipo_alerta_descripcion,
                ca.nombre AS configuracion_nombre,
                a.nivel,
                CASE a.nivel
                    WHEN 'CRITICO' THEN 3
                    WHEN 'RIESGO' THEN 2
                    WHEN 'ATENCION' THEN 1
                    ELSE 0
                END AS severidad_numerica,
                a.estado,
                a.descripcion,
                a.fecha_generacion,
                COALESCE(seg.total_seguimientos, 0) AS total_seguimientos,
                COALESCE(seg.seguimientos_abiertos, 0) AS seguimientos_abiertos,
                seg.ultimo_seguimiento,
                seg.ultima_accion,
                seg.ultimo_resultado
            FROM alertas_alertatemprana a
            INNER JOIN academico_estudiante e
                ON e.id = a.estudiante_id
            INNER JOIN academico_grupo g
                ON g.id = e.grupo_id
            INNER JOIN academico_grado gr
                ON gr.id = g.grado_id
            LEFT JOIN alertas_tipoalerta ta
                ON ta.id = a.tipo_alerta_id
            LEFT JOIN alertas_configuracionalerta ca
                ON ca.id = a.configuracion_id
            LEFT JOIN (
                SELECT
                    s.alerta_id,
                    COUNT(*) AS total_seguimientos,
                    COUNT(*) FILTER (
                        WHERE s.resultado IN ('PENDIENTE', 'EN_PROCESO')
                    ) AS seguimientos_abiertos,
                    MAX(s.fecha_registro) AS ultimo_seguimiento,
                    (
                        ARRAY_AGG(s.accion ORDER BY s.fecha_registro DESC, s.id DESC)
                    )[1] AS ultima_accion,
                    (
                        ARRAY_AGG(s.resultado ORDER BY s.fecha_registro DESC, s.id DESC)
                    )[1] AS ultimo_resultado
                FROM alertas_seguimientoalerta s
                GROUP BY s.alerta_id
            ) seg
                ON seg.alerta_id = a.id;
        """,
        "vw_powerbi_riesgo_estudiante": """
            CREATE OR REPLACE VIEW vw_powerbi_riesgo_estudiante AS
            WITH alertas_activas AS (
                SELECT
                    a.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY a.estudiante_id
                        ORDER BY
                            CASE a.nivel
                                WHEN 'CRITICO' THEN 3
                                WHEN 'RIESGO' THEN 2
                                WHEN 'ATENCION' THEN 1
                                ELSE 0
                            END DESC,
                            a.fecha_generacion DESC,
                            a.id DESC
                    ) AS orden_principal
                FROM alertas_alertatemprana a
                WHERE a.estado = 'ACTIVA'
            ),
            resumen_alertas AS (
                SELECT
                    a.estudiante_id,
                    COUNT(*) AS alertas_activas,
                    COUNT(*) FILTER (WHERE a.nivel = 'CRITICO') AS alertas_criticas,
                    COUNT(*) FILTER (WHERE a.nivel = 'RIESGO') AS alertas_riesgo,
                    COUNT(*) FILTER (WHERE a.nivel = 'ATENCION') AS alertas_atencion,
                    MAX(
                        CASE a.nivel
                            WHEN 'CRITICO' THEN 3
                            WHEN 'RIESGO' THEN 2
                            WHEN 'ATENCION' THEN 1
                            ELSE 0
                        END
                    ) AS severidad_maxima
                FROM alertas_activas a
                GROUP BY a.estudiante_id
            ),
            alerta_principal AS (
                SELECT
                    a.estudiante_id,
                    a.nivel AS nivel_riesgo_principal,
                    ta.nombre AS tipo_alerta_principal,
                    a.descripcion AS descripcion_alerta_principal,
                    a.fecha_generacion AS fecha_alerta_principal
                FROM alertas_activas a
                LEFT JOIN alertas_tipoalerta ta
                    ON ta.id = a.tipo_alerta_id
                WHERE a.orden_principal = 1
            ),
            promedio_estudiante AS (
                SELECT
                    c.estudiante_id,
                    ROUND(AVG(c.nota)::numeric, 2) AS promedio_general,
                    COUNT(*) AS total_calificaciones
                FROM evaluacion_calificacion c
                GROUP BY c.estudiante_id
            ),
            asistencias_estudiante AS (
                SELECT
                    a.estudiante_id,
                    COUNT(*) FILTER (WHERE a.estado = 'A') AS ausencias_registro,
                    COUNT(DISTINCT CASE WHEN a.estado = 'A' THEN a.fecha END) AS ausencias_distintas,
                    COUNT(DISTINCT CASE WHEN a.estado = 'T' THEN a.fecha END) AS tardes_distintas,
                    COUNT(DISTINCT CASE WHEN a.estado = 'J' THEN a.fecha END) AS justificadas_distintas,
                    COUNT(DISTINCT a.fecha) AS dias_con_registro
                FROM asistencia_asistencia a
                GROUP BY a.estudiante_id
            ),
            materias_promedio AS (
                SELECT
                    c.estudiante_id,
                    asig.nombre AS asignatura_nombre,
                    ROUND(AVG(c.nota)::numeric, 2) AS promedio_asignatura
                FROM evaluacion_calificacion c
                INNER JOIN evaluacion_actividadevaluativa act
                    ON act.id = c.actividad_id
                INNER JOIN academico_cargaacademica carga
                    ON carga.id = act.carga_academica_id
                INNER JOIN academico_asignatura asig
                    ON asig.id = carga.asignatura_id
                GROUP BY c.estudiante_id, asig.nombre
            ),
            materias_riesgo AS (
                SELECT
                    mp.estudiante_id,
                    COUNT(*) FILTER (WHERE mp.promedio_asignatura < 3.0) AS materias_en_riesgo,
                    STRING_AGG(
                        mp.asignatura_nombre || ' (' || mp.promedio_asignatura || ')',
                        ', ' ORDER BY mp.promedio_asignatura, mp.asignatura_nombre
                    ) FILTER (WHERE mp.promedio_asignatura < 3.0) AS detalle_materias_riesgo
                FROM materias_promedio mp
                GROUP BY mp.estudiante_id
            ),
            seguimientos_estudiante AS (
                SELECT
                    a.estudiante_id,
                    COUNT(s.id) AS total_seguimientos,
                    COUNT(s.id) FILTER (
                        WHERE s.resultado IN ('PENDIENTE', 'EN_PROCESO')
                    ) AS seguimientos_abiertos,
                    MAX(s.fecha_registro) AS ultimo_seguimiento
                FROM alertas_alertatemprana a
                LEFT JOIN alertas_seguimientoalerta s
                    ON s.alerta_id = a.id
                GROUP BY a.estudiante_id
            )
            SELECT
                e.id AS estudiante_id,
                e.codigo AS estudiante_codigo,
                e.documento AS estudiante_documento,
                e.apellidos || ' ' || e.nombres AS estudiante_nombre,
                g.id AS grupo_id,
                g.nombre AS grupo_nombre,
                gr.id AS grado_id,
                gr.nombre AS grado_nombre,
                gr.nombre || g.nombre AS grado_grupo,
                COALESCE(ra.alertas_activas, 0) AS alertas_activas,
                COALESCE(ra.alertas_criticas, 0) AS alertas_criticas,
                COALESCE(ra.alertas_riesgo, 0) AS alertas_riesgo,
                COALESCE(ra.alertas_atencion, 0) AS alertas_atencion,
                CASE COALESCE(ra.severidad_maxima, 0)
                    WHEN 3 THEN 'CRITICO'
                    WHEN 2 THEN 'RIESGO'
                    WHEN 1 THEN 'ATENCION'
                    ELSE 'SIN_ALERTA'
                END AS nivel_riesgo_principal,
                ap.tipo_alerta_principal,
                ap.descripcion_alerta_principal,
                ap.fecha_alerta_principal,
                pe.promedio_general,
                COALESCE(pe.total_calificaciones, 0) AS total_calificaciones,
                COALESCE(ae.ausencias_registro, 0) AS ausencias_registro,
                COALESCE(ae.ausencias_distintas, 0) AS ausencias_distintas,
                COALESCE(ae.tardes_distintas, 0) AS tardes_distintas,
                COALESCE(ae.justificadas_distintas, 0) AS justificadas_distintas,
                COALESCE(ae.dias_con_registro, 0) AS dias_con_registro,
                COALESCE(mr.materias_en_riesgo, 0) AS materias_en_riesgo,
                mr.detalle_materias_riesgo,
                COALESCE(se.total_seguimientos, 0) AS total_seguimientos,
                COALESCE(se.seguimientos_abiertos, 0) AS seguimientos_abiertos,
                se.ultimo_seguimiento,
                (
                    COALESCE(ra.severidad_maxima, 0) * 100
                    + COALESCE(ra.alertas_activas, 0) * 10
                    + COALESCE(mr.materias_en_riesgo, 0) * 5
                    + COALESCE(ae.ausencias_distintas, 0)
                ) AS indice_prioridad,
                CASE
                    WHEN COALESCE(ra.severidad_maxima, 0) = 3 THEN 'Intervencion inmediata'
                    WHEN COALESCE(ra.severidad_maxima, 0) = 2 THEN 'Seguimiento prioritario'
                    WHEN COALESCE(ra.severidad_maxima, 0) = 1 THEN 'Monitoreo preventivo'
                    ELSE 'Sin alerta activa'
                END AS estado_general
            FROM academico_estudiante e
            INNER JOIN academico_grupo g
                ON g.id = e.grupo_id
            INNER JOIN academico_grado gr
                ON gr.id = g.grado_id
            LEFT JOIN resumen_alertas ra
                ON ra.estudiante_id = e.id
            LEFT JOIN alerta_principal ap
                ON ap.estudiante_id = e.id
            LEFT JOIN promedio_estudiante pe
                ON pe.estudiante_id = e.id
            LEFT JOIN asistencias_estudiante ae
                ON ae.estudiante_id = e.id
            LEFT JOIN materias_riesgo mr
                ON mr.estudiante_id = e.id
            LEFT JOIN seguimientos_estudiante se
                ON se.estudiante_id = e.id
            WHERE e.activo = TRUE;
        """,
        "vw_powerbi_alertas_grupo": """
            CREATE OR REPLACE VIEW vw_powerbi_alertas_grupo AS
            SELECT
                grado_id,
                grado_nombre,
                grupo_id,
                grupo_nombre,
                grado_grupo,
                COUNT(*) AS estudiantes_activos,
                COUNT(*) FILTER (WHERE alertas_activas > 0) AS estudiantes_con_alerta,
                COUNT(*) FILTER (WHERE nivel_riesgo_principal = 'CRITICO') AS estudiantes_criticos,
                COUNT(*) FILTER (WHERE nivel_riesgo_principal = 'RIESGO') AS estudiantes_riesgo,
                COUNT(*) FILTER (WHERE nivel_riesgo_principal = 'ATENCION') AS estudiantes_atencion,
                ROUND(AVG(promedio_general)::numeric, 2) AS promedio_general_grupo,
                ROUND(AVG(ausencias_distintas)::numeric, 2) AS ausencias_promedio,
                ROUND(AVG(materias_en_riesgo)::numeric, 2) AS materias_riesgo_promedio,
                SUM(alertas_activas) AS alertas_activas_total,
                SUM(alertas_criticas) AS alertas_criticas_total,
                MAX(indice_prioridad) AS max_indice_prioridad
            FROM vw_powerbi_riesgo_estudiante
            GROUP BY grado_id, grado_nombre, grupo_id, grupo_nombre, grado_grupo;
        """,
    }

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write(
                self.style.WARNING(
                    "Este comando esta pensado para PostgreSQL. "
                    "La conexion actual no es PostgreSQL."
                )
            )
            return

        with connection.cursor() as cursor:
            for view_name, sql in self.VIEW_SQL.items():
                cursor.execute(sql)
                self.stdout.write(self.style.SUCCESS(f"Vista actualizada: {view_name}"))

        self.stdout.write(self.style.SUCCESS("Vistas Power BI de alertas creadas correctamente."))
