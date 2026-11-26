# Metodología de estimación de inversión

## Clases MINVU (material de la estructura soportante)

| Clase | Material | Uso típico en JMS |
|---|---|---|
| A | Acero (perfiles laminados o soldados) | Naves industriales, edificios de estructura metálica |
| B | Hormigón armado o mixta acero-hormigón | Edificios, salas eléctricas, plantas de proceso |
| C | Albañilería de ladrillo armada o confinada | Casinos, camarines, oficinas de 1 a 3 pisos |
| D | Albañilería de bloques o piedra | Bodegas menores, cierres, salas técnicas |
| E | Madera (entramados o pilares) | Viviendas, oficinas livianas, construcción en madera |
| F | Adobe o materiales tradicionales | Patrimonio, rehabilitación |
| G | Acero galvanizado liviano (tipo Metalcon) | Módulos, ampliaciones livianas |
| H | Paneles autosoportantes de madera (SIP) | Construcción industrializada |
| I | Fibrocemento, resinas o polímeros | Módulos prefabricados |

Galpones y bodegas ("Otras obras"): las dos letras indican estructura y cubierta (A acero, B hormigón, C albañilería, E madera). Ej.: AA = estructura y cubierta de acero; BA = estructura de hormigón con cubierta de acero. Categorías a (gran envergadura), b (corriente), c (ligera).

## Categorías de calidad (edificación)

1 Superior · 2 Buena · 3 Mediana · 4 Regular · 5 Deficiente. La categoría depende del diseño, la estructura, las instalaciones y las terminaciones. Si el usuario no la indica, proponerla según el uso (por ejemplo, oficinas corporativas 2; naves industriales con terminaciones básicas 3 o 4) y declararla como supuesto.

## Valores oficiales y costo de mercado

La tabla MINVU fija el presupuesto oficial sobre el que la DOM cobra los derechos de edificación. No es un costo de mercado: suele estar bajo los precios reales y no distingue bien entre materiales. Para estimar inversión:

1. Partir de la tabla MINVU vigente (base trazable y oficial).
2. Calibrar el **factor de mercado** con presupuestos adjudicados o cotizaciones recientes de JMS. Ejemplo: si un galpón de acero real costó 6,5 UF/m² y la tabla da 2,1 UF/m², el factor para esa clase es cercano a 3,1.
3. Guardar los factores calibrados por clase (campo `factores_clase` del JSON de entrada) para reutilizarlos en las próximas estimaciones.

## Reajuste trimestral

MINVU reajusta la tabla cada trimestre mediante un oficio que fija un factor sobre la resolución exenta anual (Res. Ex. N° 2016 de 2025 para 2026). Para actualizar: valor nuevo = valor base × factor, redondeado al entero. Revisar minvu.gob.cl al comenzar cada estimación.

## Recargos (orden de cálculo de la planilla)

1. Costo directo = Σ (superficie × UF/m² ajustado), o Σ partidas.
2. \+ Gastos generales y utilidades (% sobre costo directo) = subtotal construcción.
3. \+ Contingencia y honorarios (% sobre subtotal construcción) = total neto.
4. \+ IVA 19 % sobre el neto = **total de inversión estimada**.

Si los valores unitarios usados ya incluyen gastos generales y utilidades (por ejemplo, precios de contratista), dejar esos porcentajes en 0 %.

## Contingencia orientativa por nivel de definición

Referencia: clasificación de estimaciones AACE International 18R-97.

| Nivel de definición | Clase AACE | Contingencia sugerida | Exactitud esperada |
|---|---|---|---|
| Perfil o idea | 5 | 25–30 % | −50 % / +100 % |
| Conceptual o factibilidad | 4 | 20–25 % | −30 % / +50 % |
| Anteproyecto o ingeniería básica | 3 | 10–15 % | −20 % / +30 % |
| Ingeniería de detalle | 2 | 5–10 % | −15 % / +20 % |

## Exclusiones habituales (declarar en Notas)

Terreno, permisos y derechos municipales, mecánica de suelos, equipos de proceso, mobiliario, urbanización exterior, empalmes eléctricos y sanitarios fuera del predio, y gastos financieros.
