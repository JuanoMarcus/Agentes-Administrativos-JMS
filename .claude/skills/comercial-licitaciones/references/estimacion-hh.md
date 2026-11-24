# Estimación de HH y costos

## Categorías profesionales (ajustar a la estructura real de JMS)

| Código | Categoría |
|---|---|
| JP | Jefe de proyecto / ingeniero especialista |
| IS | Ingeniero senior |
| IN | Ingeniero de proyecto |
| PD | Proyectista / dibujante CAD-BIM |
| TP | Topógrafo / ayudante de terreno |
| AD | Apoyo administrativo y control documental |

Las tarifas (CLP/HH o UF/HH) y el costo empresa por categoría los entrega JMS. Nunca suponerlos.

## Método 1: histórico (preferido)

1. Buscar proyectos cerrados de la misma disciplina y nivel de desarrollo.
2. Normalizar por un indicador de tamaño: m² construidos (edificación), toneladas de acero o m³ de hormigón (estructuras industriales), metros de red o número de arranques (sanitaria), hectáreas o número de puntos (geomensura), kWp (fotovoltaico), número de láminas.
3. Calcular HH por unidad y aplicar al nuevo proyecto con un factor de complejidad (0,8–1,3) justificado por escrito.
4. Reportar el rango (mínimo–promedio–máximo) de los comparables, no solo un número.

## Método 2: paramétrico por entregable (cuando no hay histórico)

Por cada entregable: HH = cantidad × HH unitarias por categoría. Ejemplo de estructura de la tabla:

Disciplina | Etapa | Entregable | Unidad | Cantidad | HH JP | HH IS | HH IN | HH PD | HH TP | HH AD | Total HH

Agregar actividades transversales que suelen olvidarse: coordinación con otras especialidades, reuniones con el mandante, respuesta a observaciones (10–20 % de las HH de diseño según el número de rondas), control de calidad y revisión interna (5–10 %), gestión del proyecto (8–12 %), visitas a terreno.

## Del costo al precio

1. Costo de HH = Σ HH × costo empresa por categoría.
2. \+ Gastos directos (traslados, viáticos, arriendo de equipos, laboratorio, subcontratos, impresión, derechos).
3. \+ Contingencia según el riesgo identificado en las bases (típicamente 5–15 %).
4. \+ Gastos generales y margen objetivo de JMS (pedir al usuario el margen objetivo).
5. Precio = costo total / (1 − margen objetivo).
6. Comparar con el presupuesto disponible y con los precios adjudicados históricos. Si el precio para ganar deja un margen bajo el mínimo, informarlo explícitamente.

## Al adjudicarse

Exportar la tabla de HH por disciplina, etapa y categoría como línea base para `gestion-control-proyectos`.
