# Cubicación desde planos e itemizado desde especificaciones técnicas

## 1. Documentos de entrada y cómo leerlos

| Documento | Herramienta | Qué extraer |
|---|---|---|
| DXF | `scripts/leer_dxf.py` | Largos por capa, áreas de polilíneas cerradas, conteo de bloques, textos y cotas |
| DWG | Pedir exportación a DXF o PDF | — |
| PDF vectorial | `scripts/leer_pdf_plano.py` | Texto, cuadros (armaduras, vanos, terminaciones), escala, códigos de elementos, imágenes por página |
| PDF escaneado o imagen | Lectura visual de las imágenes | Medidas acotadas; declarar "leído de imagen" |
| Especificaciones técnicas (PDF o Word) | `leer_pdf_plano.py` o lectura directa | Partidas, materiales, calidades, espesores, normas, alcances y exclusiones |
| Planillas de armaduras o listas de materiales | Lectura directa (Excel, PDF) | kg de acero por elemento, perfiles y pesos |
| Modelo IFC | No hay lector instalado: pedir planillas de cantidades exportadas del modelo | Cantidades por elemento |

Reglas:
- **Solo medidas acotadas o leídas de capas o tablas.** No medir a escala sobre una imagen salvo que no haya otra opción; en ese caso, declararlo en Observaciones con la escala usada.
- Registrar en cada fila de cubicación el plano y su revisión (ej.: "E-01 Rev B, planta de fundaciones").
- Si dos documentos se contradicen (plano vs ET, planta vs corte), usar el más desfavorable y anotarlo como consulta.
- Lo que no esté definido se marca **SUPUESTO** en Observaciones, con su criterio (ej.: cuantía de acero 60 kg/m³ hasta tener la planilla de armaduras).

## 2. Del itemizado de las ET a las partidas

1. Si las ET traen itemizado numerado, **respetar su numeración y su texto**: es lo que el mandante comparará.
2. Si no lo traen, usar la estructura tipo de abajo y agregar los ítems que las ET describan.
3. Cada partida lleva: ítem, capítulo, descripción, unidad, referencia de ET (columna Especificación técnica).
4. Revisar que cada material o calidad exigida en las ET esté cubierta por algún ítem, y que cada elemento dibujado en los planos tenga su ítem.

### Estructura tipo (edificación e industrial)

| Capítulo | Partidas típicas | Unidad |
|---|---|---|
| 1. Obras provisorias y trabajos preliminares | Instalación de faenas, cierros, letreros, trazado y niveles, aseo | gl, ml, m² |
| 2. Movimiento de tierras | Escarpe, excavación, relleno compactado, retiro de excedentes | m³ |
| 3. Fundaciones | Emplantillado, hormigón, acero de refuerzo, moldaje, pernos de anclaje | m³, kg, m², un |
| 4. Obra gruesa | Sobrecimientos, muros, pilares, vigas, losas, escaleras (hormigón, enfierradura, moldaje); albañilería | m³, kg, m² |
| 5. Estructura metálica | Perfiles, planchas, conexiones, pintura, montaje | kg |
| 6. Estructura de madera | Pilares, vigas, entramados, paneles, tratamiento | m³, ml, m² |
| 7. Cubierta y hojalatería | Costaneras, cubierta, aislación, canales, bajadas, forros | kg, m², ml |
| 8. Pavimentos | Radier, base estabilizada, pavimentos interiores y exteriores | m², m³ |
| 9. Terminaciones | Tabiques, revestimientos, cielos, pinturas, puertas, ventanas | m², un |
| 10. Instalaciones | Sanitarias, eléctricas, gas, clima, red húmeda y seca | gl, ml, un |
| 11. Obras exteriores | Pavimentos exteriores, cierros, aguas lluvias, paisajismo | m², ml |

## 3. Criterios de medición

Confirmar con JMS o con las bases del mandante; si estas fijan otro criterio, prevalecen.

| Partida | Criterio |
|---|---|
| Excavación | Volumen geométrico del elemento + sobreexcavación de trabajo si la ET la define |
| Hormigón | Volumen geométrico neto, sin descontar armaduras ni insertos |
| Acero de refuerzo | kg de la planilla de armaduras (incluye traslapos dibujados); pérdidas en el APU |
| Moldaje | m² de superficie de hormigón en contacto con el moldaje |
| Albañilería | m² de muro, descontando vanos según criterio de las bases |
| Acero estructural | kg de la lista de materiales; conexiones y pernos como % declarado si no están detallados |
| Cubierta | m² en verdadera magnitud (proyección × factor de pendiente); traslapos en el APU |
| Radier | m² en planta, descontando fundaciones solo si las bases lo indican |
| Pintura | m² de superficie a pintar |
| Puertas, ventanas, artefactos | Unidades, por tipo del cuadro de vanos |

En la hoja Cubicación, una fila por elemento o grupo de elementos iguales: N° veces × largo × ancho × alto, o una cantidad directa cuando venga de una planilla o del DXF.
