# Tablero de indicadores para gerencia (mensual)

## Fila 1: alertas
- Meses proyectados con caja bajo el colchón mínimo.
- Facturas vencidas > 60 días.
- Proyectos con semáforo rojo (de `gestion-control-proyectos`).
- Licitaciones con cierre en los próximos 15 días (de `comercial-desarrollo`).

## Fila 2: KPI principales
| KPI | Definición |
|---|---|
| Facturación del mes y acumulada del año | Facturas emitidas (CLP) vs meta |
| Backlog | Saldo por ejecutar de contratos vigentes |
| Pipeline ponderado | Σ monto × probabilidad |
| Meses de backlog | Backlog / facturación mensual promedio |
| Margen bruto de cartera | (Ingresos − costo directo) / ingresos |
| Utilización del equipo | HH facturables / HH disponibles |
| DSO | Días promedio de cobro |
| Caja proyectada a 90 días | Escenario base |
| Tasa de adjudicación | Propuestas ganadas / presentadas (últimos 12 meses) |

## Fila 3: análisis
- Margen y facturación por disciplina (barras).
- Evolución mensual de facturación, cobranza y caja (líneas).
- Utilización por categoría profesional.
- Antigüedad de cuentas por cobrar por tramo.

## Preguntas que el tablero debe responder
- ¿Tenemos caja para los próximos 3 meses?
- ¿Qué disciplinas y clientes son más rentables?
- ¿Necesitamos contratar o tenemos capacidad ociosa?
- ¿El pipeline alcanza para sostener la facturación del próximo semestre?
