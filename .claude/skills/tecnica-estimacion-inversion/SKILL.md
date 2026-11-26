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
  version: "0.3.0"
---

# Agente de Estimación de Inversión

Objetivo: a partir de planos y especificaciones técnicas, **armar el itemizado, cubicar cada ítem, desarrollar el análisis de precio unitario (APU) de cada uno y calcular la inversión por ítem, capítulo y total**, en el formato de Cuadro de Precios (CDP) de JMS, en pesos y en UF, en una planilla Excel donde el valor de la UF y todos los supuestos se pueden cambiar.

Si todavía no hay planos (etapa de perfil), hacer la estimación paramétrica por m² y material (paso 7) y declararla como orden de magnitud.

## Flujo de trabajo

### 1. Recibir y ordenar los antecedentes

- Pedir o leer: planos (DXF, PDF o imágenes), especificaciones técnicas, itemizado oficial si existe, planillas de armaduras o listas de materiales, cotizaciones disponibles.
- Hacer una lista de documentos con código y revisión. Va al campo `documentos_base` y a la hoja Notas.
- Para un DWG, pedir que lo exporten a DXF o PDF. Para un modelo IFC, usar `scripts/ifc_cantidades.py` (volumen, áreas y largos por tipo, material y nivel); filtrar los elementos del entorno (terreno, edificios vecinos) por posición y contrastar con los planos de cálculo.

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
- DXF con muchas capas o referencias externas: `dxf_vista.py --buscar TEXTO` ubica títulos y rótulos, y `--png --ventana x0 y0 x1 y1 --capas ...` dibuja una zona ampliada solo con las capas de estructura para leer cotas y secciones.
- PDF: `leer_pdf_plano.py` extrae texto, cuadros, escala y códigos de elementos, y genera una imagen de cada página. Revisar las imágenes para leer cotas, cortes y detalles.
- Una fila de cubicación por elemento o grupo de elementos iguales: N° veces × largo × ancho × alto, o una cantidad directa si viene de una planilla o del DXF. Siempre con plano y revisión de origen.
- Criterios de medición en `references/cubicacion-itemizado.md`, sección 3.
- Nunca inventar medidas. Lo no definido va como **SUPUESTO** en Observaciones, con su criterio. Las contradicciones entre documentos se listan como consultas.

### 4. Análisis de precios unitarios (formato JMS)

Seguir `references/apu.md`:

- **Antes de partir de cero, buscar cuadros de precios anteriores de JMS** (SharePoint o adjuntos) y convertirlos con:
  ```bash
  python3 .claude/skills/tecnica-estimacion-inversion/scripts/extraer_cdp.py cuadro_anterior.xlsx trabajo/<proyecto>/base_cdp.json
  ```
  Reutilizar APU de ítems iguales o parecidos y su base de materiales y tarifas, **actualizando precios y fechas**.
- Un bloque APU por ítem con MATERIALES, MANO DE OBRA (HD, costo $/HD de la tabla de tarifas, LS %) y MAQ. Y EQUIPOS (costo, vida útil). Las cantidades son totales del ítem, escritas como fórmula (personas × días); el rendimiento se calcula solo.
- Precios en la base MATERIALES (con proveedor y fecha) y tarifas en «Mano de obra». Si una partida se cotiza completa, usar el P. Unit. directo con su origen.
- Nunca inventar precios ni rendimientos. Lo que falte se deja pendiente o se marca REFERENCIAL con su fuente.

### 5. Valor de la UF y recargos

- UF del día desde el SII o el Banco Central, con fecha y fuente. Si no hay acceso a la web, pedirla al usuario.
- Recargos del cuadro: gastos generales y utilidades sobre el costo directo (en el CDP-001: 25 % y 12 %), imprevistos si corresponde, IVA 19 %. Leyes sociales para la mano de obra (28 % en el CDP-001). Confirmar para cada proyecto.

### 6. Generar el cuadro de precios

1. Escribir el JSON de entrada con el formato de `assets/ejemplo_entrada.json`: datos del proyecto, `partidas` (con capítulo y subcapítulo), `cubicacion`, `materiales`, `mano_obra`, `apu`, `referencias`.
2. Ejecutar:
   ```bash
   python3 .claude/skills/tecnica-estimacion-inversion/scripts/generar_planilla.py entrada.json salida.xlsx
   ```
3. Recalcular (si existe la skill `xlsx`, con su `recalc.py`) y confirmar cero errores de fórmula.
4. Revisar a mano al menos tres ítems: una cantidad de la cubicación, un P. Unit. de su APU y su total.

| Hoja | Contenido |
|---|---|
| Parámetros | UF editable, GG, utilidades, imprevistos, IVA, leyes sociales, superficie |
| CDP | Cuadro de precios JMS: encabezado, ítems por capítulo y subcapítulo, P. Unit. y Total en $ y UF, subtotales, CD, GG, utilidades, neto, IVA, bruto, observaciones |
| Resumen | Directo por capítulo, %, $/m², UF/m², recargos y rango ±20 % |
| Cubicación | Memoria de cálculo por ítem, con plano de origen y supuestos |
| APU (capítulo) | Un bloque por ítem: materiales, mano de obra y equipos |
| MATERIALES, Mano de obra | Bases de precios y tarifas |
| Estimación m², Comparación materiales, Tabla MINVU | Contraste paramétrico por superficie y material |
| Sensibilidad UF, Referencias, Notas | Total en pesos para otras UF, fuentes de precios, supuestos y exclusiones |

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
