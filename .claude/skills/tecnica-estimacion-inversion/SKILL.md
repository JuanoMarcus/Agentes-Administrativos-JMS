---
name: tecnica-estimacion-inversion
description: >
  Agente de Estimación de Inversión de JMS (área Técnica). This skill should be used when the user asks
  for an "estimado de inversión", "presupuesto", "presupuesto estimativo", "cubicar", "cubicación",
  "itemizado", "análisis de precios unitarios", "APU", "leer los planos y las especificaciones técnicas",
  "cuánto cuesta construir", "costo por m2", "presupuesto DOM", "tabla de costos unitarios MINVU",
  "comparar hormigón armado vs albañilería vs acero vs madera", "galpón", "bodega", or wants a planilla
  with montos en UF y en pesos and the option to change the valor de la UF.
metadata:
  version: "0.2.0"
---

# Agente de Estimación de Inversión

Objetivo: a partir de planos y especificaciones técnicas, **armar el itemizado, cubicar cada ítem, desarrollar el análisis de precio unitario (APU) de cada uno y calcular la inversión por ítem, capítulo y total**, en UF y en pesos, en una planilla Excel donde el valor de la UF y todos los supuestos se pueden cambiar.

Si todavía no hay planos (etapa de perfil), hacer la estimación paramétrica por m² y material (paso 7) y declararla como orden de magnitud.

## Flujo de trabajo

### 1. Recibir y ordenar los antecedentes

- Pedir o leer: planos (DXF, PDF o imágenes), especificaciones técnicas, itemizado oficial si existe, planillas de armaduras o listas de materiales, cotizaciones disponibles.
- Hacer una lista de documentos con código y revisión. Va al campo `documentos_base` y a la hoja Notas.
- Para un DWG, pedir que lo exporten a DXF o PDF. Para un modelo IFC, pedir las planillas de cantidades exportadas.

### 2. Leer las especificaciones técnicas y armar el itemizado

Seguir `references/cubicacion-itemizado.md`, secciones 1 y 2:

- Si las ET o las bases traen itemizado, respetar su numeración y su texto.
- Si no, usar la estructura tipo y crear un ítem por cada partida que describan las ET.
- Por ítem: capítulo, descripción, unidad y referencia de ET (material, calidad, espesor, norma).
- Cruzar en ambos sentidos: todo lo que piden las ET tiene ítem, y todo elemento dibujado tiene ítem.

Para leer un PDF:

```bash
python3 .claude/skills/tecnica-estimacion-inversion/scripts/leer_pdf_plano.py ET.pdf trabajo/<proyecto>/lectura_ET
```

### 3. Cubicar desde los planos

- DXF:
  ```bash
  python3 .claude/skills/tecnica-estimacion-inversion/scripts/leer_dxf.py plano.dxf --json trabajo/<proyecto>/dxf.json
  ```
  Entrega largos por capa, áreas de polilíneas cerradas, conteo de bloques, textos y cotas. Confirmar la unidad del dibujo con una cota conocida.
- PDF: `leer_pdf_plano.py` extrae texto, cuadros, escala y códigos de elementos, y genera una imagen de cada página. Revisar las imágenes para leer cotas, cortes y detalles.
- Una fila de cubicación por elemento o grupo de elementos iguales: N° veces × largo × ancho × alto, o una cantidad directa si viene de una planilla o del DXF. Siempre con plano y revisión de origen.
- Criterios de medición en `references/cubicacion-itemizado.md`, sección 3.
- Nunca inventar medidas. Lo no definido va como **SUPUESTO** en Observaciones, con su criterio. Las contradicciones entre documentos se listan como consultas.

### 4. Análisis de precios unitarios

Seguir `references/apu.md`:

- Cargar en la lista de insumos cada material, categoría de mano de obra, equipo y subcontrato, con precio (CLP o UF), fuente y fecha.
- Por cada ítem, un APU con sus líneas: tipo, código de insumo, cantidad o rendimiento por unidad de partida, % de pérdida y nota de origen.
- Si una partida se cotiza completa, usar el P.U. directo en la partida, con su origen.
- Nunca inventar precios ni rendimientos. Lo que falte se deja pendiente o se marca REFERENCIAL con su fuente.

### 5. Valor de la UF y recargos

- UF del día desde el SII o el Banco Central, con fecha y fuente. Si no hay acceso a la web, pedirla al usuario.
- Recargos: gastos generales, utilidades, contingencia (según nivel de definición, `references/metodologia.md`), honorarios e IVA (19 %). Leyes sociales y herramientas menores para los APU.

### 6. Generar la planilla

1. Escribir el JSON de entrada con el formato de `assets/ejemplo_entrada.json`: `partidas`, `cubicacion`, `insumos`, `apu`, además de los parámetros. Guardarlo en `trabajo/<proyecto>/`.
2. Ejecutar:
   ```bash
   python3 .claude/skills/tecnica-estimacion-inversion/scripts/generar_planilla.py entrada.json salida.xlsx
   ```
3. Recalcular (si existe la skill `xlsx`, con su `recalc.py`) y confirmar cero errores de fórmula.
4. Revisar a mano al menos tres ítems: una cantidad de la cubicación, un P.U. de su APU y su total.

| Hoja | Contenido |
|---|---|
| Parámetros | UF editable, recargos, leyes sociales, herramientas menores, superficie total |
| Resumen | Costo directo por capítulo, % de cada uno, recargos, IVA, total, UF/m² y contraste con la estimación paramétrica |
| Partidas | Itemizado: cantidad (desde Cubicación), P.U. (desde su APU), total UF y CLP, % y referencia de ET |
| Cubicación | Memoria de cálculo por ítem, con plano de origen y supuestos |
| Insumos | Precios de materiales, mano de obra, equipos y subcontratos, en UF o CLP, con fuente |
| APU <ítem> | Una hoja por partida con su análisis de precio unitario |
| Estimación m², Comparación materiales, Tabla MINVU | Estimación paramétrica por superficie y material, para contrastar |
| Sensibilidad UF | Total en pesos para distintos valores de UF |
| Notas | Documentos base, fuentes, supuestos y exclusiones |

### 7. Estimación paramétrica (sin planos o para contrastar)

Recintos con superficie, clase de material y categoría MINVU (`references/metodologia.md` y `references/tabla_minvu_2026_t4.json`). Revisar si hay un reajuste trimestral MINVU más reciente. La tabla MINVU no es precio de mercado: usar los factores de mercado y por clase calibrados con datos de JMS, o dejarlos en 1,00 y decirlo.

### 8. Entregar

- Enviar el .xlsx y resumir: total en UF y CLP, UF/m², los tres capítulos de mayor incidencia, valor y fecha de la UF.
- Listar los **supuestos**, las **consultas** (contradicciones o faltantes en planos y ET) y los **precios pendientes**.
- Si va a una propuesta o licitación, coordinar con `comercial-licitaciones`.

## Reglas

- Cantidades y montos siempre con fórmulas en la planilla, trazables al plano y al APU.
- Mostrar UF y CLP, con el valor y la fecha de la UF usada.
- Separar datos de supuestos; citar fuentes de precios y rendimientos.
- El agente asiste: la revisión y aprobación del presupuesto corresponde al profesional responsable de JMS.
