# Tablero Power BI de Alertas

Este paquete deja listo el modelo de datos y el diseno funcional del tablero de alertas para Power BI Desktop.

## Archivos incluidos

- `docs/powerbi/powerbi_theme_alertas.json`: tema visual listo para importar.
- `docs/powerbi/powerbi_alertas_measures.dax`: medidas DAX base.
- `alertas/management/commands/crear_vistas_powerbi_alertas.py`: comando para crear las vistas en PostgreSQL.

## Vistas a usar

Usa estas tres vistas como base:

- `vw_powerbi_riesgo_estudiante`
- `vw_powerbi_alertas_detalle`
- `vw_powerbi_alertas_grupo`

## Orden recomendado en Power BI Desktop

1. `Obtener datos`
2. `PostgreSQL`
3. Servidor: `localhost:5433`
4. Base de datos: `plataforma_academica_v2`
5. Carga las tres vistas anteriores
6. Importa el tema `powerbi_theme_alertas.json`
7. Crea una tabla de medidas y pega `powerbi_alertas_measures.dax`

## Relaciones recomendadas

- `vw_powerbi_riesgo_estudiante[estudiante_id]` -> `vw_powerbi_alertas_detalle[estudiante_id]`
- `vw_powerbi_riesgo_estudiante[grado_grupo]` -> `vw_powerbi_alertas_grupo[grado_grupo]`

Direccion de filtro recomendada: simple, desde `vw_powerbi_riesgo_estudiante`.

## Pagina 1: Resumen Ejecutivo

Visuales:

- Tarjeta: `Estudiantes Con Alerta`
- Tarjeta: `Estudiantes Criticos`
- Tarjeta: `Promedio General Dashboard`
- Tarjeta: `Ausencias Promedio`
- Dona: `nivel_riesgo_principal`
- Barra: `tipo_alerta_principal` por `Estudiantes Con Alerta`
- Barra horizontal: `grado_grupo` por `alertas_activas_total`
- Tabla Top 10: estudiante, grupo, tipo principal, promedio, ausencias, materias en riesgo, prioridad

Filtros visuales:

- `Top Prioridad <= 10`

## Pagina 2: Priorizacion de Casos

Segmentadores:

- `grado_nombre`
- `grupo_nombre`
- `nivel_riesgo_principal`
- `tipo_alerta_principal`

Visuales:

- Tabla principal con:
  - `estudiante_nombre`
  - `grado_grupo`
  - `nivel_riesgo_principal`
  - `tipo_alerta_principal`
  - `promedio_general`
  - `ausencias_distintas`
  - `materias_en_riesgo`
  - `seguimientos_abiertos`
  - `indice_prioridad`
- Tarjeta: `Estudiantes Sin Seguimiento`
- Tarjeta: `Seguimientos Abiertos`

## Pagina 3: Seguimiento Operativo

Base: `vw_powerbi_alertas_detalle`

Visuales:

- Tarjeta: `Alertas Activas Detalle`
- Tarjeta: `Criticas Activas`
- Tarjeta: `Alertas Sin Seguimiento`
- Tarjeta: `Alertas Con Seguimiento Abierto`
- Barras: `tipo_alerta` por cantidad
- Barras apiladas: `nivel` por `estado`
- Tabla detalle:
  - `estudiante_nombre`
  - `grado_grupo`
  - `tipo_alerta`
  - `nivel`
  - `estado`
  - `fecha_generacion`
  - `total_seguimientos`
  - `seguimientos_abiertos`
  - `ultima_accion`
  - `ultimo_resultado`

## Recomendaciones visuales

- Usa rojo para `CRITICO`, naranja para `RIESGO`, amarillo para `ATENCION`.
- Ordena por `indice_prioridad` descendente.
- No uses la tabla de detalle como portada del reporte.
- Usa `ausencias_distintas`, no `ausencias_registro`, para decisiones ejecutivas.

## Recomendacion tecnica

Si luego quieres ver evolucion en el tiempo, el siguiente paso no es tocar el dashboard sino crear una tabla snapshot diaria o semanal, por ejemplo:

- `vw_powerbi_snapshot_riesgo_estudiante`

Con eso ya podras hacer tendencias reales de crecimiento o reduccion del riesgo.
