# Tablero Power BI - Analitica academica y alertas tempranas

Este paquete prepara la base para un tablero en Power BI conectado a PostgreSQL. La idea es no construir los visuales directamente sobre las tablas transaccionales de Django, sino sobre vistas analiticas limpias.

## 1. Vistas incluidas

Ejecuta el script `docs/powerbi/powerbi_views.sql` en la base `plataforma_academica_v2`.

Vistas principales:

- `powerbi_dim_estudiante`: estudiantes con grado, grupo y datos de acudiente.
- `powerbi_dim_carga_academica`: asignatura, grupo, grado, docente y ano lectivo.
- `powerbi_dim_periodo`: periodos academicos.
- `powerbi_fact_asistencia`: registros de asistencia con banderas para presente, ausente, tarde y justificado.
- `powerbi_fact_actividad_evaluativa`: actividades evaluativas y porcentaje.
- `powerbi_fact_calificacion`: notas por actividad, desempeno y aporte ponderado.
- `powerbi_fact_alerta`: alertas tempranas generadas por el sistema.
- `powerbi_fact_seguimiento_alerta`: intervenciones registradas sobre cada alerta, responsable, accion, resultado y proxima revision.
- `powerbi_mart_seguimiento_estudiante`: resumen de intervenciones por estudiante para indicadores de gestion de casos.
- `powerbi_mart_riesgo_estudiante`: resumen consolidado por estudiante con promedio, asistencia, alertas, seguimientos y nivel de riesgo integral.

## 2. Conexion desde Power BI Desktop

1. Abre Power BI Desktop.
2. Selecciona `Obtener datos`.
3. Elige `Base de datos PostgreSQL`.
4. Servidor: `localhost:5433`.
5. Base de datos: `plataforma_academica_v2`.
6. Modo recomendado: `Importar` para el prototipo academico.
7. Selecciona las vistas que empiezan por `powerbi_`.

Si Power BI no muestra el conector PostgreSQL, instala el proveedor requerido por Power BI Desktop para PostgreSQL y vuelve a intentar.

## 3. Modelo sugerido

Relaciones recomendadas:

- `powerbi_dim_estudiante[estudiante_id]` con `powerbi_fact_asistencia[estudiante_id]`.
- `powerbi_dim_estudiante[estudiante_id]` con `powerbi_fact_calificacion[estudiante_id]`.
- `powerbi_dim_estudiante[estudiante_id]` con `powerbi_fact_alerta[estudiante_id]`.
- `powerbi_dim_estudiante[estudiante_id]` con `powerbi_fact_seguimiento_alerta[estudiante_id]`.
- `powerbi_fact_alerta[alerta_id]` con `powerbi_fact_seguimiento_alerta[alerta_id]`.
- `powerbi_dim_carga_academica[carga_academica_id]` con `powerbi_fact_asistencia[carga_academica_id]`.
- `powerbi_dim_carga_academica[carga_academica_id]` con `powerbi_fact_calificacion[carga_academica_id]`.
- `powerbi_dim_periodo[periodo_id]` con `powerbi_fact_calificacion[periodo_id]`.

Tambien puedes usar `powerbi_mart_riesgo_estudiante` y `powerbi_mart_seguimiento_estudiante` como tablas resumen independientes para visuales ejecutivos.

## 4. Medidas DAX sugeridas

```DAX
Total Estudiantes =
DISTINCTCOUNT(powerbi_dim_estudiante[estudiante_id])
```

```DAX
Promedio Nota =
AVERAGE(powerbi_fact_calificacion[nota])
```

```DAX
Porcentaje Bajo Desempeno =
DIVIDE(
    SUM(powerbi_fact_calificacion[bajo_desempeno]),
    COUNTROWS(powerbi_fact_calificacion),
    0
)
```

```DAX
Porcentaje Asistencia =
DIVIDE(
    SUM(powerbi_fact_asistencia[presente]),
    COUNTROWS(powerbi_fact_asistencia),
    0
)
```

```DAX
Total Ausencias =
SUM(powerbi_fact_asistencia[ausente])
```

```DAX
Alertas Activas =
SUM(powerbi_fact_alerta[alerta_activa])
```

```DAX
Alertas Criticas Activas =
SUM(powerbi_fact_alerta[alerta_critica_activa])
```

```DAX
Total Seguimientos =
COUNTROWS(powerbi_fact_seguimiento_alerta)
```

```DAX
Alertas Con Seguimiento =
DISTINCTCOUNT(powerbi_fact_seguimiento_alerta[alerta_id])
```

```DAX
Revisiones Vencidas =
SUM(powerbi_fact_seguimiento_alerta[revision_vencida])
```

```DAX
Estudiantes En Riesgo =
CALCULATE(
    DISTINCTCOUNT(powerbi_mart_riesgo_estudiante[estudiante_id]),
    powerbi_mart_riesgo_estudiante[nivel_riesgo_integral] IN {"ATENCION", "RIESGO", "CRITICO"}
)
```

## 5. Paginas recomendadas del tablero

Pagina 1: Vista ejecutiva

- Tarjetas: total estudiantes, promedio nota, porcentaje asistencia, alertas activas, estudiantes en riesgo.
- Grafico de barras: estudiantes por nivel de riesgo integral.
- Tabla: estudiantes criticos con promedio, ausencias y alertas activas.

Pagina 2: Rendimiento academico

- Promedio por grado, grupo y asignatura.
- Porcentaje de bajo desempeno por periodo.
- Top estudiantes con menor promedio.
- Segmentadores: ano lectivo, periodo, grado, grupo, asignatura.

Pagina 3: Asistencia

- Porcentaje de asistencia general.
- Ausencias por grado/grupo.
- Tendencia de ausencias por fecha.
- Estudiantes con mas ausencias.

Pagina 4: Alertas tempranas

- Alertas por tipo, estado y nivel.
- Alertas criticas activas.
- Tabla de casos con estudiante, grupo, descripcion y fecha.

Pagina 5: Seguimiento e intervencion

- Tarjetas: total seguimientos, alertas con seguimiento, revisiones vencidas y casos con mejora.
- Grafico de barras: seguimientos por accion realizada.
- Grafico de dona: resultados de seguimiento.
- Tabla: estudiante, tipo de alerta, accion, resultado, proxima revision y responsable.

## 6. Nota metodologica

La escala usada en las vistas asume notas de `0.00` a `5.00`:

- Bajo: menor a `3.0`.
- Basico: desde `3.0` hasta menor a `4.0`.
- Alto: desde `4.0` hasta menor a `4.6`.
- Superior: desde `4.6` hasta `5.0`.

Esto es una parametrizacion institucional sugerida para el prototipo. Si tu documento define otra equivalencia con la escala nacional del Decreto 1290 de 2009, ajusta los umbrales en `powerbi_fact_calificacion` y `powerbi_mart_riesgo_estudiante`.
