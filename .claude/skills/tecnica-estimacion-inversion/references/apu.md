# Análisis de precios unitarios (APU)

## Estructura de cada hoja APU

Una hoja por partida ("APU 3.2"). Cada línea indica tipo, código del insumo, cantidad o rendimiento por unidad de partida y % de pérdida. La descripción, la unidad y el precio se traen de la hoja **Insumos**.

```
Costo directo unitario = Materiales × (1 + pérdida)
                       + Mano de obra × (1 + leyes sociales + herramientas menores)
                       + Equipos
                       + Subcontratos
```

Leyes sociales y herramientas menores son porcentajes únicos en la hoja Parámetros (C16 y C17): definirlos con los valores vigentes que use JMS.

## Cantidades y rendimientos

| Tipo | Cantidad por unidad de partida | Ejemplo de cómo se obtiene |
|---|---|---|
| Material | Consumo geométrico del material | Radier e = 12 cm → 0,12 m³ de hormigón por m² |
| Mano de obra | HH por unidad = 1 / rendimiento | Cuadrilla que hace 20 m²/día de 8 h con 2 personas → 16 HH / 20 m² = 0,8 HH/m² |
| Equipo | Horas o días de equipo por unidad | Retroexcavadora de 16 m³/hr → 0,0625 hr/m³ |
| Subcontrato | 1 unidad, a precio del subcontratista | Pintura intumescente a precio cotizado por m² |

Fuentes de rendimientos, en este orden: (1) datos reales de obras de JMS o del cliente, (2) cotizaciones de subcontratistas, (3) manuales de costos y rendimientos publicados (citar edición y página). Indicar el origen en la columna Nota de cada línea.

## Precios de insumos (hoja Insumos)

- Precios netos, sin IVA, con **fuente y fecha** (cotización, lista de precios de proveedor, contrato anterior).
- Pueden ingresarse en CLP o en UF; la planilla convierte con la UF vigente.
- Un insumo se ingresa una vez y lo usan todos los APU: si cambia un precio, se actualizan todos los ítems.
- Nunca inventar precios. Si falta uno, dejarlo vacío y listarlo en la entrega como pendiente, o usar un valor de referencia marcado "REFERENCIAL" con su fuente.

## Partidas sin APU

Si una partida se cotiza completa (estructura metálica suministrada y montada, ventanas, ascensor), ingresar su P.U. directo en la hoja Partidas, con el origen ("Cotización proveedor X, fecha").

## Control de calidad del APU

- Unidades coherentes: la cantidad de cada línea está en la unidad del insumo por unidad de la partida.
- El % de pérdida es razonable y está explicado en la nota (despuntes, traslapos, derrames).
- Comparar el P.U. resultante con históricos de JMS o con la tabla MINVU convertida a la unidad de la partida; si difiere mucho, revisar.
