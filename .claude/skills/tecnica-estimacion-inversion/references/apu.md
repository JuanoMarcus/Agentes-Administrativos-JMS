# Análisis de precios unitarios (APU) — formato JMS

Formato tomado del Cuadro de Precios CDP-001 «Of. Proyectos CMPC Santa Fe» (JMS, 2023). El generador lo replica y agrega columnas en UF.

## Bloque APU por ítem

Una hoja por capítulo, por ejemplo «APU (2.1-2.12)», con un bloque por ítem:

```
Ítem            2.3   Excavaciones de fundaciones                (vínculo al CDP)
Cantidad Ppto.  627,6  m3     Pre. Unit. ($) = Σ subtotales      Total Neto ($) = P.U. × cantidad
                              Pre. Unit. (UF)                    Total Neto (UF)

MATERIALES          Unidad  Cantidad  Rendto. = Cantidad / Cant. Ppto.  Pérdida %  Precio $/un  Subtotal = Rendto × (1 + pérdida) × Precio
MANO DE OBRA        HD      Cantidad (HD)  Rendto. (HD/unid.)  Costo $/HD  LS %  Subtotal = Rendto × Costo × (1 + LS)
MAQ. Y EQUIPOS      Unidad  Cantidad  Rendto. (d/unid.)  Costo $  Vida útil (d)  Subtotal = Rendto × Costo / Vida útil
```

- **Las cantidades del APU son totales del ítem** (por ejemplo, «=2*5» = 2 personas × 5 días). El rendimiento por unidad sale de dividir por la cantidad del cuadro de precios. Escribir la cantidad como fórmula aritmética (personas × días, unidades × meses) para que se entienda el supuesto.
- **Mano de obra:** costo $/HD = costo mensual de la especialidad / 30, desde la hoja «Mano de obra». Leyes sociales: 28 % en el CDP-001 (parámetro único en la hoja Parámetros).
- **Equipos:** vida útil 1 = arriendo por día (el costo es el valor diario); vida útil 365 = herramienta propia (el costo es el valor de compra, que se prorratea por día de uso).
- **Partidas globales (gl)** con cantidad 1: el APU suma directamente los recursos del ítem (por ejemplo, 14 meses de contenedor + 6 días de camión pluma).

## Bases de precios

- **MATERIALES:** categoría, código (hor., mad., fij., rev., ace., equ., her.), correlativo, descripción, unidad, precio $, rendimiento o nota, proveedor y fecha. Clave = código + correlativo (ej.: «hor.1004»). Una línea de APU con código toma descripción, unidad y precio de esta base.
- **Mano de obra:** especialidad, $/mes líquido, $/mes costo, $/día.
- **Referencias:** fuentes usadas por JMS: ONDAC (APU y rendimientos), Sodimac, Easy, Rental Essentials (arriendo de equipos), Multiaceros, Cintac, OAP (aceros), Zigma (cañerías), Topex (adhesivos).
- Precios netos, sin IVA, con **fuente y fecha**. Nunca inventar precios: si falta uno, dejarlo pendiente o marcarlo REFERENCIAL con su fuente.

## Reutilizar cuadros anteriores

`scripts/extraer_cdp.py` convierte un cuadro de precios JMS existente en JSON con partidas, APU, materiales, tarifas y referencias. Usarlo para:

1. Buscar ítems iguales o parecidos y reutilizar su APU (recursos, cantidades por unidad, pérdidas), ajustando cantidades al nuevo proyecto.
2. Reutilizar la base de materiales y tarifas, **actualizando precios y fechas** antes de usarlos (un precio de 2023 no sirve sin reajuste o nueva cotización).

## Recargos del cuadro de precios

Costo directo + gastos generales (% sobre CD) + utilidades (% sobre CD) + imprevistos (si se usan) = total neto; + IVA 19 % = total bruto. En el CDP-001: GG 25 % y utilidades 12 %. Confirmar para cada proyecto.

## Controles antes de entregar

- **Cada APU divide por su propia cantidad.** En el CDP-001 había dos bloques que dividían por la cantidad de otro ítem (3.6.3 y 3.7.1). El generador evita este error porque cada bloque usa su propia celda de cantidad; al copiar bloques a mano, revisarlo.
- Unidades coherentes entre la cantidad del recurso y su precio (sacos, planchas, cajas, m²).
- Pérdidas razonables y explicadas.
- Comparar P.U. con cuadros anteriores de JMS y con la estimación paramétrica (hoja Estimación m²).
