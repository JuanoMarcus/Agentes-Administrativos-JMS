---
name: tecnica-estimacion-inversion
description: >
  Agente de Estimación de Inversión de JMS (área Técnica). This skill should be used when the user asks
  for an "estimado de inversión", "estimación de costos", "presupuesto estimativo", "cuánto cuesta construir",
  "costo por m2", "orden de magnitud", "presupuesto DOM", "tabla de costos unitarios MINVU", "comparar
  hormigón armado vs albañilería vs acero vs madera", "galpón", "bodega", or wants a planilla with
  montos en UF y en pesos, with the option to change the valor de la UF.
metadata:
  version: "0.1.0"
---

# Agente de Estimación de Inversión

Objetivo: entregar estimaciones de inversión de proyectos de construcción en Chile, en **UF y en pesos**, en una planilla Excel donde el usuario pueda **cambiar el valor de la UF** y los supuestos, y todo se recalcule.

## Flujo de trabajo

### 1. Reunir los datos del proyecto

Pedir solo lo que falte:

- Nombre del proyecto, mandante y ubicación (comuna y región).
- Recintos o edificaciones: descripción y superficie en m².
- Material estructural de cada uno: hormigón armado, albañilería reforzada (ladrillo o bloques), acero, madera, acero galvanizado liviano, u otro.
- Calidad o nivel de terminaciones → categoría MINVU (1 superior, 2 buena, 3 mediana, 4 regular, 5 deficiente). Para galpones y bodegas: a (gran envergadura), b (corriente), c (ligera).
- Nivel de definición del proyecto (perfil, anteproyecto, ingeniería básica, detalle): fija la contingencia.
- Si hay cubicaciones o partidas con cantidades, usar además la hoja **Partidas**.

Si el usuario no indica categoría, proponer la más probable y decirlo como supuesto.

### 2. Valor de la UF

Buscar el valor de la UF del día en el SII (sii.cl, valores y fechas → UF) o en el Banco Central. Registrar valor, fecha y fuente. Si no hay acceso a la web, pedirlo al usuario. Nunca usar un valor de memoria sin advertirlo.

### 3. Costos unitarios

- Base: **Tabla de costos unitarios por m² de construcción del MINVU**, en `references/tabla_minvu_2026_t4.json` (4.° trimestre 2026). Leer `references/metodologia.md` para clases, categorías y su uso.
- Antes de usarla, comprobar si MINVU publicó un reajuste trimestral más reciente. Si existe, actualizar el JSON (valores × factor de reajuste, redondeados al entero) y la fuente.
- La tabla MINVU es la base oficial para derechos municipales y suele quedar bajo el costo de mercado. Ajustarla así:
  - **Factor de mercado** global (hoja Parámetros), calibrado con presupuestos reales de JMS o cotizaciones.
  - **Factor por clase** (hoja Tabla MINVU, columna G), para diferenciar acero, albañilería y hormigón, que MINVU trata parecido.
  - **Factor regional**, por aislamiento o logística (Aysén, Magallanes, islas, zonas mineras).
- No inventar factores. Si no hay datos para calibrar, dejarlos en 1,00 y decirlo en la entrega.

### 4. Recargos

Definir con el usuario o declarar como supuesto: gastos generales, utilidades, contingencia, honorarios de ingeniería y arquitectura, e IVA (19 %). Contingencia orientativa por nivel de definición en `references/metodologia.md`.

### 5. Generar la planilla

1. Escribir un JSON de entrada con el formato de `assets/ejemplo_entrada.json` (en `trabajo/<proyecto>/` si existe esa carpeta).
2. Ejecutar:
   ```bash
   python3 .claude/skills/tecnica-estimacion-inversion/scripts/generar_planilla.py entrada.json salida.xlsx
   ```
3. Recalcular y revisar que no haya errores de fórmula. Si está disponible la skill `xlsx`, usar su `recalc.py`.
4. Revisar a mano al menos un recinto: superficie × CLP/m² = subtotal en pesos.

La planilla tiene estas hojas:

| Hoja | Contenido |
|---|---|
| Parámetros | Valor UF (editable), factores y recargos. Cambiar la UF recalcula todo. |
| Tabla MINVU | Costos unitarios oficiales en CLP/m², factor por clase y conversión a UF/m². |
| Estimación | Un recinto por fila: m², clase, categoría, UF/m², subtotal UF y CLP; resumen con recargos e IVA. |
| Comparación materiales | Misma superficie en hormigón armado, albañilería, acero, madera y galpones. |
| Partidas | Presupuesto por cantidades y precios unitarios en UF, cuando hay cubicaciones. |
| Sensibilidad UF | Total en pesos para distintos valores de la UF. |
| Notas | Fuentes, supuestos, exclusiones y alcance. |

### 6. Entregar

- Enviar el .xlsx y resumir en el chat: total en UF y en pesos, incidencia en UF/m², valor UF usado y supuestos principales.
- Marcar la estimación como **referencial (orden de magnitud)**. No es un presupuesto de construcción.
- Si la estimación va a una propuesta, coordinar con `comercial-licitaciones`.

## Reglas

- Todos los montos se calculan con fórmulas en la planilla, nunca a mano.
- Mostrar siempre UF y CLP, con el valor y la fecha de la UF usada.
- Separar datos (del usuario o de fuentes) de supuestos, y citar las fuentes en la hoja Notas.
- La revisión y aprobación del monto corresponde al profesional responsable de JMS.
