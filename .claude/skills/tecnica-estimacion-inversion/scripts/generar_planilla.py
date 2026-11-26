#!/usr/bin/env python3
"""Genera la planilla Excel de estimación de inversión JMS (UF y CLP, UF variable).

Uso:
    python3 generar_planilla.py entrada.json salida.xlsx

Entrada: JSON con el proyecto (ver ../assets/ejemplo_entrada.json). Puede traer:
  - recintos     → estimación paramétrica por m² y material (tabla MINVU)
  - partidas     → itemizado (ítem, capítulo, descripción, unidad, ET de referencia)
  - cubicacion   → memoria de cubicación por ítem (N° veces × largo × ancho × alto, o cantidad directa)
  - insumos      → lista de precios de materiales, mano de obra, equipos y subcontratos (UF o CLP)
  - apu          → análisis de precios unitarios por ítem (líneas que usan códigos de insumos)

Todo queda como fórmulas: al cambiar la UF, un precio de insumo, un rendimiento o una
medida de la cubicación, se recalculan los APU, las partidas, los capítulos y los totales.
"""
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

AQUI = Path(__file__).resolve().parent
TABLA = json.loads((AQUI.parent / "references" / "tabla_minvu_2026_t4.json").read_text(encoding="utf-8"))

# --- estilos -----------------------------------------------------------------
F = "Arial"
f_norm = Font(name=F, size=10)
f_bold = Font(name=F, size=10, bold=True)
f_tit = Font(name=F, size=14, bold=True, color="1F2A44")
f_sub = Font(name=F, size=11, bold=True, color="1F2A44")
f_inp = Font(name=F, size=10, color="0000FF")
f_link = Font(name=F, size=10, color="008000")
f_link_b = Font(name=F, size=10, color="008000", bold=True)
f_note = Font(name=F, size=9, italic=True, color="595959")
f_warn = Font(name=F, size=9, italic=True, color="C00000")
fill_inp = PatternFill("solid", fgColor="FFFF00")
fill_head = PatternFill("solid", fgColor="D9DEE5")
fill_tot = PatternFill("solid", fgColor="EEF1F5")
fill_cap = PatternFill("solid", fgColor="F4F6F9")
thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
FMT_UF = '#,##0.00;(#,##0.00);"-"'
FMT_UF4 = '#,##0.0000;(#,##0.0000);"-"'
FMT_CLP = '"$"#,##0;("$"#,##0);"-"'
FMT_PCT = '0.0%;(0.0%);"-"'
FMT_Q = '#,##0.00;(#,##0.00);"-"'
FMT_Q3 = '#,##0.000;(#,##0.000);"-"'
FMT_X = '0.00"x"'
CENTER = Alignment(horizontal="center")
WRAP = Alignment(wrap_text=True, vertical="top")

P = "'Parámetros'"
UF = f"{P}!$C$5"
FR = f"{P}!$C$7"
FM = f"{P}!$C$8"
GG = f"{P}!$C$10"
UT = f"{P}!$C$11"
CO = f"{P}!$C$12"
HO = f"{P}!$C$13"
IV = f"{P}!$C$14"
LS = f"{P}!$C$16"
HM = f"{P}!$C$17"
SUP = f"{P}!$C$18"

TIPOS = ["Material", "Mano de obra", "Equipo", "Subcontrato"]


def cell(ws, ref, value, font=f_norm, fmt=None, fill=None, border=True, align=None):
    c = ws[ref]
    c.value = value
    c.font = font
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if border:
        c.border = box
    if align:
        c.alignment = align
    return c


def header(ws, row, titles, col0=1):
    for i, t in enumerate(titles):
        cell(ws, f"{get_column_letter(col0 + i)}{row}", t, f_bold, fill=fill_head,
             align=Alignment(wrap_text=True, vertical="center", horizontal="center"))
    ws.row_dimensions[row].height = 30


def widths(ws, ws_widths):
    for col, w in ws_widths.items():
        ws.column_dimensions[col].width = w


def qs(name):
    """Referencia a hoja, siempre entre comillas."""
    return "'" + name.replace("'", "''") + "'"


def apu_sheet_name(item):
    bad = '[]:*?/\\'
    s = "".join("-" if ch in bad else ch for ch in str(item))
    return ("APU " + s)[:31]


def resumen_recargos(ws, row, ref_directo_uf, etiqueta="Costo directo"):
    """Bloque Costo directo → GG → Utilidades → Contingencia → Honorarios → Neto → IVA → Total.
    Columnas B a E. Devuelve la fila del total."""
    header(ws, row, ["Concepto", "Base de cálculo", "Monto (UF)", "Monto (CLP)"], col0=2)
    r = row + 1
    filas = [
        (etiqueta, "Suma de ítems o recintos", f"={ref_directo_uf}"),
        ("Gastos generales", "% sobre costo directo", f"=D{r}*{GG}"),
        ("Utilidades", "% sobre costo directo", f"=D{r}*{UT}"),
        ("Subtotal construcción", "Directo + GG + utilidades", f"=SUM(D{r}:D{r+2})"),
        ("Contingencia", "% sobre subtotal construcción", f"=D{r+3}*{CO}"),
        ("Honorarios ingeniería / arquitectura", "% sobre subtotal construcción", f"=D{r+3}*{HO}"),
        ("Total neto", "Subtotal + contingencia + honorarios", f"=D{r+3}+D{r+4}+D{r+5}"),
        ("IVA", "% sobre total neto", f"=D{r+6}*{IV}"),
        ("TOTAL INVERSIÓN ESTIMADA", "Neto + IVA", f"=D{r+6}+D{r+7}"),
    ]
    for i, (lab, base, f_uf) in enumerate(filas):
        rr = r + i
        bold = lab in ("Subtotal construcción", "Total neto", "TOTAL INVERSIÓN ESTIMADA")
        fill = fill_tot if bold else None
        cell(ws, f"B{rr}", lab, f_bold if bold else f_norm, fill=fill)
        cell(ws, f"C{rr}", base, f_note, fill=fill)
        cell(ws, f"D{rr}", f_uf, f_bold if bold else f_norm, FMT_UF, fill)
        cell(ws, f"E{rr}", f"=D{rr}*{UF}", f_bold if bold else f_norm, FMT_CLP, fill)
    return r + len(filas) - 1


# =============================================================================
def main(entrada, salida):
    d = json.loads(Path(entrada).read_text(encoding="utf-8"))
    wb = Workbook()

    partidas = d.get("partidas") or []
    cubic = d.get("cubicacion") or []
    insumos = d.get("insumos") or []
    apus = d.get("apu") or {}
    detalle = bool(partidas)

    # ---------------- Parámetros ----------------
    ws = wb.active
    ws.title = "Parámetros"
    cell(ws, "B1", "Estimación de inversión — JMS Ingenieros Consultores", f_tit, border=False)
    cell(ws, "B2", f"{d.get('proyecto', '[Proyecto]')} · {d.get('mandante', '[Mandante]')} · {d.get('ubicacion', '[Ubicación]')}",
         f_sub, border=False)
    cell(ws, "B3", d.get("documentos_base", ""), f_note, border=False)
    header(ws, 4, ["Parámetro", "Valor", "Nota / fuente"], col0=2)
    params = [
        (5, "Valor de la UF (CLP)", d["uf"], '"$"#,##0.00', d.get("fuente_uf", "Ingresado por el usuario")),
        (6, "Fecha del valor UF", d.get("fecha_uf", ""), None, "Fecha a la que corresponde el valor UF"),
        (7, "Factor regional", d.get("factor_regional", 1.0), FMT_X, d.get("nota_factor_regional", "1,00 = sin ajuste. Ajustar por zona (aislamiento, logística)")),
        (8, "Factor de mercado sobre tabla MINVU", d.get("factor_mercado", 1.0), FMT_X, d.get("nota_factor_mercado", "Solo estimación por m². 1,00 = valor oficial MINVU. Calibrar con presupuestos reales")),
        (10, "Gastos generales", d.get("gastos_generales", 0.0), FMT_PCT, "% sobre costo directo"),
        (11, "Utilidades", d.get("utilidades", 0.0), FMT_PCT, "% sobre costo directo"),
        (12, "Contingencia", d.get("contingencia", 0.0), FMT_PCT, "Según nivel de definición (ver hoja Notas)"),
        (13, "Honorarios ingeniería / arquitectura", d.get("honorarios", 0.0), FMT_PCT, "% sobre subtotal construcción"),
        (14, "IVA", d.get("iva", 0.19), FMT_PCT, "Tasa general IVA Chile"),
        (16, "Leyes sociales (APU)", d.get("leyes_sociales", 0.0), FMT_PCT, d.get("nota_leyes_sociales", "% sobre mano de obra en cada APU. Definir con valores vigentes de JMS")),
        (17, "Herramientas menores (APU)", d.get("herramientas_menores", 0.0), FMT_PCT, "% sobre mano de obra en cada APU"),
        (18, "Superficie construida total (m²)", d.get("superficie_total"), '#,##0.0', "Para calcular la incidencia en UF/m²"),
    ]
    for r, lab, val, fmt, nota in params:
        cell(ws, f"B{r}", lab, f_bold)
        cell(ws, f"C{r}", val, f_inp, fmt, fill_inp)
        cell(ws, f"D{r}", nota, f_note, align=Alignment(wrap_text=True))
    cell(ws, "B9", "Recargos", f_sub, border=False)
    cell(ws, "B15", "Análisis de precios unitarios", f_sub, border=False)
    cell(ws, "B20", "Cómo usar esta planilla", f_sub, border=False)
    guia = [
        "Celdas con fondo amarillo y texto azul: datos que puede cambiar. Texto verde: vínculo a otra hoja. Negro: fórmula.",
        "Cambie la UF en C5 y se recalculan todos los montos en pesos.",
        "Resumen: inversión por capítulo y total con recargos e IVA.",
        "Partidas: itemizado con cantidad (desde Cubicación) y precio unitario (desde su hoja APU), total por ítem.",
        "Cubicación: memoria de cálculo de cada cantidad, con el plano o documento de origen.",
        "Insumos: precios de materiales, mano de obra, equipos y subcontratos, en UF o en pesos.",
        "Hojas APU: análisis de precio unitario de cada ítem (cantidades, rendimientos, pérdidas y precios).",
        "Estimación m², Comparación materiales y Tabla MINVU: estimación paramétrica por superficie, para contrastar.",
        "Estimación de apoyo. La revisión y aprobación corresponde al profesional responsable de JMS.",
    ]
    for i, t in enumerate(guia):
        cell(ws, f"B{21 + i}", f"• {t}", f_norm, border=False)
    widths(ws, {"A": 2, "B": 38, "C": 16, "D": 80})

    # ---------------- Tabla MINVU ----------------
    wt = wb.create_sheet("Tabla MINVU")
    cell(wt, "A1", "Costos unitarios por m² de construcción — MINVU", f_tit, border=False)
    cell(wt, "A2", TABLA["fuente"], f_note, border=False)
    header(wt, 4, ["Clave", "Clase", "Material / estructura", "Categoría", "Calidad", "CLP/m² (oficial)",
                   "Factor de ajuste por clase (editable)", "CLP/m² ajustado", "UF/m² ajustado (UF vigente)"])
    factores = d.get("factores_clase", {})
    r = 5
    for fila in TABLA["filas"]:
        if fila["clp_m2"] is None:
            continue
        cell(wt, f"A{r}", f'{fila["clase"]}-{fila["categoria"]}')
        cell(wt, f"B{r}", fila["clase"])
        cell(wt, f"C{r}", fila["material"])
        cell(wt, f"D{r}", fila["categoria"])
        cell(wt, f"E{r}", fila["calidad"])
        cell(wt, f"F{r}", fila["clp_m2"], f_inp, FMT_CLP)
        cell(wt, f"G{r}", factores.get(fila["clase"], 1.0), f_inp, FMT_X, fill_inp)
        cell(wt, f"H{r}", f"=F{r}*G{r}", f_norm, FMT_CLP)
        cell(wt, f"I{r}", f"=H{r}/{UF}", f_norm, FMT_UF)
        r += 1
    t_last = r - 1
    cell(wt, f"A{r + 1}", TABLA["nota"], f_note, border=False)
    cell(wt, f"A{r + 2}", "La tabla MINVU asigna el mismo valor a acero (A), albañilería de ladrillo (C) y de bloques (D). "
         "Use el factor de ajuste por clase (columna G) para diferenciar materiales según presupuestos reales de JMS.",
         f_note, border=False)
    widths(wt, {"A": 9, "B": 7, "C": 48, "D": 10, "E": 22, "F": 16, "G": 18, "H": 16, "I": 18})
    wt.freeze_panes = "A5"
    KEY = f"'Tabla MINVU'!$A$5:$A${t_last}"
    VAL = f"'Tabla MINVU'!$H$5:$H${t_last}"
    clases = sorted({f["clase"] for f in TABLA["filas"]}, key=lambda c: (len(c), c))

    # ---------------- Estimación m² ----------------
    we = wb.create_sheet("Estimación m²")
    cell(we, "A1", "Estimación paramétrica por superficie y material", f_tit, border=False)
    cell(we, "A2", "UF vigente:", f_bold, border=False)
    cell(we, "B2", f"={UF}", f_link, '"$"#,##0.00', border=False)
    header(we, 4, ["Recinto / edificación", "Superficie (m²)", "Clase", "Categoría", "Clave",
                   "CLP/m² (tabla ajustada)", "UF/m² ajustado", "Subtotal (UF)", "Subtotal (CLP)"])
    recintos = d.get("recintos") or []
    n_rows = max(len(recintos) + 5, 10)
    first, last = 5, 5 + n_rows - 1
    for i in range(n_rows):
        rr = first + i
        rec = recintos[i] if i < len(recintos) else {}
        cell(we, f"A{rr}", rec.get("descripcion"), f_inp, fill=fill_inp)
        cell(we, f"B{rr}", rec.get("superficie"), f_inp, '#,##0.0;(#,##0.0);"-"', fill_inp)
        cell(we, f"C{rr}", rec.get("clase"), f_inp, fill=fill_inp, align=CENTER)
        cell(we, f"D{rr}", str(rec["categoria"]) if rec.get("categoria") is not None else None, f_inp, fill=fill_inp, align=CENTER)
        cell(we, f"E{rr}", f'=IF(C{rr}="","",C{rr}&"-"&D{rr})', align=CENTER)
        cell(we, f"F{rr}", f'=IF(E{rr}="","",IFERROR(INDEX({VAL},MATCH(E{rr},{KEY},0)),"sin valor"))', fmt=FMT_CLP)
        cell(we, f"G{rr}", f'=IF(ISNUMBER(F{rr}),F{rr}/{UF}*{FR}*{FM},"")', fmt=FMT_UF)
        cell(we, f"H{rr}", f'=IF(ISNUMBER(G{rr}),B{rr}*G{rr},0)', fmt=FMT_UF)
        cell(we, f"I{rr}", f"=H{rr}*{UF}", fmt=FMT_CLP)
    tr = last + 1
    cell(we, f"A{tr}", "Total", f_bold, fill=fill_tot)
    cell(we, f"B{tr}", f"=SUM(B{first}:B{last})", f_bold, '#,##0.0', fill_tot)
    for col in "CDEFG":
        cell(we, f"{col}{tr}", None, fill=fill_tot)
    cell(we, f"H{tr}", f"=SUM(H{first}:H{last})", f_bold, FMT_UF, fill_tot)
    cell(we, f"I{tr}", f"=H{tr}*{UF}", f_bold, FMT_CLP, fill_tot)
    dv_c = DataValidation(type="list", formula1='"' + ",".join(clases) + '"', allow_blank=True)
    dv_k = DataValidation(type="list", formula1='"1,2,3,4,5,a,b,c"', allow_blank=True)
    we.add_data_validation(dv_c)
    we.add_data_validation(dv_k)
    dv_c.add(f"C{first}:C{last}")
    dv_k.add(f"D{first}:D{last}")
    cell(we, f"A{tr + 2}", "Resumen de la estimación paramétrica", f_sub, border=False)
    tot_e = resumen_recargos(we, tr + 3, f"H{tr}", "Costo directo (recintos)")
    cell(we, f"G{tot_e - 1}", "Incidencia total", f_note, border=False)
    cell(we, f"G{tot_e}", f"=IF(B{tr}>0,D{tot_e}/B{tr},0)", f_bold, '#,##0.00" UF/m²"', fill_tot)
    widths(we, {"A": 40, "B": 22, "C": 18, "D": 16, "E": 16, "F": 18, "G": 18, "H": 16, "I": 18})
    we.freeze_panes = "A5"
    REF_PARAM = f"'Estimación m²'!$D${tot_e}"
    REF_PARAM_DIR = f"'Estimación m²'!$H${tr}"

    # ---------------- Comparación materiales ----------------
    wc = wb.create_sheet("Comparación materiales")
    comp = d.get("comparar") or {}
    cell(wc, "A1", "Comparación por material estructural (paramétrica)", f_tit, border=False)
    cell(wc, "A3", "Superficie (m²)", f_bold)
    cell(wc, "B3", comp.get("superficie", 1000), f_inp, '#,##0.0', fill_inp)
    cell(wc, "A4", "Categoría de edificación (1 a 5)", f_bold)
    cell(wc, "B4", str(comp.get("categoria", 3)), f_inp, fill=fill_inp, align=CENTER)
    cell(wc, "A5", "Galpón o bodega: categoría (a, b, c)", f_bold)
    cell(wc, "B5", str(comp.get("categoria_galpon", "b")), f_inp, fill=fill_inp, align=CENTER)
    dv_e = DataValidation(type="list", formula1='"1,2,3,4,5"', allow_blank=False)
    dv_g = DataValidation(type="list", formula1='"a,b,c"', allow_blank=False)
    wc.add_data_validation(dv_e)
    wc.add_data_validation(dv_g)
    dv_e.add("B4")
    dv_g.add("B5")
    cell(wc, "D3", "Factor de recargos (GG, utilidades, contingencia, honorarios, IVA)", f_note, border=False)
    cell(wc, "D4", f"=(1+{GG}+{UT})*(1+{CO}+{HO})*(1+{IV})", f_bold, FMT_X)
    header(wc, 7, ["Material", "Clase MINVU", "UF/m² directo", "Costo directo (UF)", "Total con recargos e IVA (UF)",
                   "Total con recargos e IVA (CLP)", "Diferencia vs referencia"])
    mats = [
        ("Hormigón armado", "B", "B4"), ("Albañilería de ladrillo (armada o confinada)", "C", "B4"),
        ("Albañilería de bloques", "D", "B4"), ("Acero estructural", "A", "B4"), ("Madera", "E", "B4"),
        ("Acero galvanizado liviano (tipo Metalcon)", "G", "B4"),
        ("Galpón: estructura y cubierta de acero", "AA", "B5"), ("Galpón: estructura de hormigón, cubierta de acero", "BA", "B5"),
        ("Galpón: estructura de albañilería, cubierta de acero", "CA", "B5"), ("Galpón: estructura y cubierta de madera", "EE", "B5"),
    ]
    r0 = 8
    for i, (lab, cl, catref) in enumerate(mats):
        rr = r0 + i
        cell(wc, f"A{rr}", lab, f_bold if i in (0, 6) else f_norm)
        cell(wc, f"B{rr}", cl, align=CENTER)
        cell(wc, f"C{rr}", f'=IFERROR(INDEX({VAL},MATCH(B{rr}&"-"&${catref[0]}${catref[1:]},{KEY},0))/{UF}*{FR}*{FM},"sin valor")', fmt=FMT_UF)
        cell(wc, f"D{rr}", f'=IF(ISNUMBER(C{rr}),C{rr}*$B$3,"sin valor")', fmt=FMT_UF)
        cell(wc, f"E{rr}", f'=IF(ISNUMBER(D{rr}),D{rr}*$D$4,"sin valor")', fmt=FMT_UF)
        cell(wc, f"F{rr}", f'=IF(ISNUMBER(E{rr}),E{rr}*{UF},"sin valor")', fmt=FMT_CLP)
        base = f"$E${r0}" if i < 6 else f"$E${r0 + 6}"
        cell(wc, f"G{rr}", f'=IF(AND(ISNUMBER(E{rr}),ISNUMBER({base})),E{rr}/{base}-1,"")', fmt='+0.0%;-0.0%;"-"')
    cell(wc, f"A{r0 + len(mats) + 1}", "Filas 1 a 6: edificación, diferencia respecto de hormigón armado. "
         "Filas 7 a 10: galpones y bodegas, diferencia respecto del galpón de acero.", f_note, border=False)
    widths(wc, {"A": 50, "B": 14, "C": 16, "D": 20, "E": 24, "F": 26, "G": 22})

    # ---------------- Insumos ----------------
    wi = wb.create_sheet("Insumos")
    cell(wi, "A1", "Lista de precios de insumos", f_tit, border=False)
    cell(wi, "A2", "Precios netos (sin IVA). Ingrese el precio en UF o en CLP (columna Moneda); la planilla convierte con la UF vigente.", f_note, border=False)
    header(wi, 4, ["Código", "Descripción", "Unidad", "Tipo", "Precio", "Moneda", "Precio (UF)", "Precio (CLP)", "Fuente y fecha del precio"])
    n_i = max(len(insumos) + 15, 25)
    if_, il = 5, 5 + n_i - 1
    for i in range(n_i):
        rr = if_ + i
        it = insumos[i] if i < len(insumos) else {}
        cell(wi, f"A{rr}", it.get("codigo"), f_inp, fill=fill_inp)
        cell(wi, f"B{rr}", it.get("descripcion"), f_inp, fill=fill_inp)
        cell(wi, f"C{rr}", it.get("unidad"), f_inp, fill=fill_inp, align=CENTER)
        cell(wi, f"D{rr}", it.get("tipo"), f_inp, fill=fill_inp)
        cell(wi, f"E{rr}", it.get("precio"), f_inp, '#,##0.0000;(#,##0.0000);"-"', fill_inp)
        cell(wi, f"F{rr}", it.get("moneda", "CLP") if it else None, f_inp, fill=fill_inp, align=CENTER)
        cell(wi, f"G{rr}", f'=IF(ISNUMBER(E{rr}),IF(F{rr}="CLP",E{rr}/{UF},E{rr}),"")', fmt=FMT_UF4)
        cell(wi, f"H{rr}", f'=IF(ISNUMBER(G{rr}),G{rr}*{UF},"")', fmt=FMT_CLP)
        fuente = it.get("fuente")
        cell(wi, f"I{rr}", fuente, f_warn if fuente and "EJEMPLO" in fuente.upper() else f_inp, fill=fill_inp)
    dv_t = DataValidation(type="list", formula1='"' + ",".join(TIPOS) + '"', allow_blank=True)
    dv_m = DataValidation(type="list", formula1='"CLP,UF"', allow_blank=True)
    wi.add_data_validation(dv_t)
    wi.add_data_validation(dv_m)
    dv_t.add(f"D{if_}:D{il}")
    dv_m.add(f"F{if_}:F{il}")
    widths(wi, {"A": 12, "B": 46, "C": 9, "D": 15, "E": 14, "F": 9, "G": 14, "H": 14, "I": 46})
    wi.freeze_panes = "A5"
    I_KEY = f"'Insumos'!$A${if_}:$A${il}"
    I_DESC = f"'Insumos'!$B${if_}:$B${il}"
    I_UNI = f"'Insumos'!$C${if_}:$C${il}"
    I_UF = f"'Insumos'!$G${if_}:$G${il}"

    # ---------------- APU (una hoja por ítem) ----------------
    apu_total = {}
    apu_sheets = []
    desc_by_item = {str(p.get("item")): p for p in partidas}
    for item, lineas in apus.items():
        name = apu_sheet_name(item)
        wa = wb.create_sheet(name)
        apu_sheets.append(wa)
        p = desc_by_item.get(str(item), {})
        cell(wa, "A1", "Análisis de precio unitario", f_tit, border=False)
        cell(wa, "A2", "Ítem", f_bold)
        cell(wa, "B2", str(item), f_bold)
        cell(wa, "C2", p.get("descripcion", ""), f_bold)
        cell(wa, "A3", "Unidad", f_bold)
        cell(wa, "B3", p.get("unidad", ""), align=CENTER)
        cell(wa, "C3", p.get("et", ""), f_note)
        header(wa, 5, ["Tipo", "Código insumo", "Descripción", "Unidad", "Cantidad o rendimiento por unidad de partida",
                       "% pérdida", "Precio unitario (UF)", "Parcial (UF)", "Nota (origen de la cantidad o rendimiento)"])
        orden = {t: i for i, t in enumerate(TIPOS)}
        lineas = sorted(lineas, key=lambda x: orden.get(x.get("tipo"), 9))
        n_l = len(lineas) + 3
        lf, ll = 6, 6 + n_l - 1
        for i in range(n_l):
            rr = lf + i
            ln = lineas[i] if i < len(lineas) else {}
            cell(wa, f"A{rr}", ln.get("tipo"), f_inp, fill=fill_inp)
            cell(wa, f"B{rr}", ln.get("codigo"), f_inp, fill=fill_inp, align=CENTER)
            cell(wa, f"C{rr}", f'=IF(B{rr}="","",IFERROR(INDEX({I_DESC},MATCH(B{rr},{I_KEY},0)),"código no existe en Insumos"))', f_link)
            cell(wa, f"D{rr}", f'=IF(B{rr}="","",IFERROR(INDEX({I_UNI},MATCH(B{rr},{I_KEY},0)),""))', f_link, align=CENTER)
            cell(wa, f"E{rr}", ln.get("cantidad"), f_inp, '#,##0.0000;(#,##0.0000);"-"', fill_inp)
            cell(wa, f"F{rr}", ln.get("perdida", 0) if ln else None, f_inp, FMT_PCT, fill_inp)
            cell(wa, f"G{rr}", f'=IF(B{rr}="",0,IFERROR(INDEX({I_UF},MATCH(B{rr},{I_KEY},0)),0))', f_link, FMT_UF4)
            cell(wa, f"H{rr}", f'=IF(ISNUMBER(E{rr}),E{rr}*(1+N(F{rr}))*G{rr},0)', fmt=FMT_UF4)
            cell(wa, f"I{rr}", ln.get("nota"), f_inp, fill=fill_inp)
        dv = DataValidation(type="list", formula1='"' + ",".join(TIPOS) + '"', allow_blank=True)
        wa.add_data_validation(dv)
        dv.add(f"A{lf}:A{ll}")
        s = ll + 2
        rng_t = f"$A${lf}:$A${ll}"
        rng_p = f"$H${lf}:$H${ll}"
        resumen = [
            ("Materiales", f'=SUMIF({rng_t},"Material",{rng_p})'),
            ("Mano de obra", f'=SUMIF({rng_t},"Mano de obra",{rng_p})'),
            ("Leyes sociales (% sobre mano de obra)", f"=H{s+1}*{LS}"),
            ("Herramientas menores (% sobre mano de obra)", f"=H{s+1}*{HM}"),
            ("Equipos", f'=SUMIF({rng_t},"Equipo",{rng_p})'),
            ("Subcontratos", f'=SUMIF({rng_t},"Subcontrato",{rng_p})'),
        ]
        for i, (lab, fml) in enumerate(resumen):
            cell(wa, f"F{s+i}", lab, f_norm)
            cell(wa, f"G{s+i}", None)
            cell(wa, f"H{s+i}", fml, fmt=FMT_UF4)
        t = s + len(resumen)
        cell(wa, f"F{t}", "Costo directo unitario (UF / " + str(p.get("unidad", "unidad")) + ")", f_bold, fill=fill_tot)
        cell(wa, f"G{t}", None, fill=fill_tot)
        cell(wa, f"H{t}", f"=SUM(H{s}:H{t-1})", f_bold, FMT_UF4, fill_tot)
        cell(wa, f"F{t+1}", "Costo directo unitario (CLP)", f_bold, fill=fill_tot)
        cell(wa, f"G{t+1}", None, fill=fill_tot)
        cell(wa, f"H{t+1}", f"=H{t}*{UF}", f_bold, FMT_CLP, fill_tot)
        widths(wa, {"A": 14, "B": 12, "C": 44, "D": 9, "E": 18, "F": 34, "G": 14, "H": 14, "I": 40})
        apu_total[str(item)] = f"{qs(name)}!$H${t}"

    # ---------------- Cubicación ----------------
    wq = wb.create_sheet("Cubicación")
    cell(wq, "A1", "Memoria de cubicación", f_tit, border=False)
    cell(wq, "A2", "Cantidad parcial = N° veces × largo × ancho × alto (las medidas vacías no se multiplican), o la cantidad directa si se ingresa. "
         "Cada fila indica el plano o documento de donde sale la medida.", f_note, border=False)
    header(wq, 4, ["Ítem", "Elemento / eje / ubicación", "Plano o documento de origen", "N° veces", "Largo (m)", "Ancho (m)",
                   "Alto o espesor (m)", "Cantidad directa", "Cantidad parcial", "Unidad", "Observaciones y supuestos"])
    n_q = max(len(cubic) + 30, 40)
    qf, ql = 5, 5 + n_q - 1
    n_p = max(len(partidas) + 10, 20)
    pf, pl = 5, 5 + n_p - 1
    P_ITEM = f"'Partidas'!$A${pf}:$A${pl}"
    P_UNI = f"'Partidas'!$D${pf}:$D${pl}"
    for i in range(n_q):
        rr = qf + i
        q = cubic[i] if i < len(cubic) else {}
        cell(wq, f"A{rr}", str(q["item"]) if q.get("item") is not None else None, f_inp, fill=fill_inp, align=CENTER)
        cell(wq, f"B{rr}", q.get("elemento"), f_inp, fill=fill_inp)
        cell(wq, f"C{rr}", q.get("plano"), f_inp, fill=fill_inp)
        cell(wq, f"D{rr}", q.get("veces"), f_inp, FMT_Q, fill_inp)
        cell(wq, f"E{rr}", q.get("largo"), f_inp, FMT_Q3, fill_inp)
        cell(wq, f"F{rr}", q.get("ancho"), f_inp, FMT_Q3, fill_inp)
        cell(wq, f"G{rr}", q.get("alto"), f_inp, FMT_Q3, fill_inp)
        cell(wq, f"H{rr}", q.get("cantidad"), f_inp, FMT_Q, fill_inp)
        cell(wq, f"I{rr}", f'=IF(A{rr}="","",IF(ISNUMBER(H{rr}),H{rr},IF(COUNT(E{rr}:G{rr})=0,"",IF(ISNUMBER(D{rr}),D{rr},1)*PRODUCT(E{rr}:G{rr}))))', fmt=FMT_Q)
        cell(wq, f"J{rr}", f'=IF(A{rr}="","",IFERROR(INDEX({P_UNI},MATCH(A{rr},{P_ITEM},0)),"ítem no existe"))', f_link, align=CENTER)
        cell(wq, f"K{rr}", q.get("obs"), f_inp, fill=fill_inp)
    widths(wq, {"A": 8, "B": 36, "C": 26, "D": 10, "E": 11, "F": 11, "G": 13, "H": 13, "I": 14, "J": 9, "K": 44})
    wq.freeze_panes = "A5"
    Q_ITEM = f"'Cubicación'!$A${qf}:$A${ql}"
    Q_CANT = f"'Cubicación'!$I${qf}:$I${ql}"

    # ---------------- Partidas ----------------
    wp = wb.create_sheet("Partidas")
    cell(wp, "A1", "Itemizado y presupuesto por partidas", f_tit, border=False)
    cell(wp, "A2", "Cantidad: suma de la hoja Cubicación para el ítem (o manual si no hay cubicación). "
         "P.U.: costo directo de su hoja APU (o manual si no hay APU).", f_note, border=False)
    header(wp, 4, ["Ítem", "Capítulo", "Descripción", "Unidad", "Cantidad", "Origen de la cantidad", "P.U. (UF)",
                   "Origen del P.U.", "Total (UF)", "Total (CLP)", "% del costo directo", "Especificación técnica (referencia)"])
    cub_items = {str(q.get("item")) for q in cubic}
    for i in range(n_p):
        rr = pf + i
        p = partidas[i] if i < len(partidas) else {}
        it = str(p["item"]) if p.get("item") is not None else None
        cell(wp, f"A{rr}", it, f_inp, fill=fill_inp, align=CENTER)
        cell(wp, f"B{rr}", p.get("capitulo"), f_inp, fill=fill_inp)
        cell(wp, f"C{rr}", p.get("descripcion"), f_inp, fill=fill_inp, align=Alignment(wrap_text=True))
        cell(wp, f"D{rr}", p.get("unidad"), f_inp, fill=fill_inp, align=CENTER)
        if it and it in cub_items:
            cell(wp, f"E{rr}", f'=SUMIF({Q_ITEM},A{rr},{Q_CANT})', f_link, FMT_Q)
            cell(wp, f"F{rr}", "Cubicación", f_note)
        else:
            cell(wp, f"E{rr}", p.get("cantidad"), f_inp, FMT_Q, fill_inp)
            cell(wp, f"F{rr}", p.get("origen_cantidad", "Manual") if p else None, f_note)
        if it and it in apu_total:
            cell(wp, f"G{rr}", f"={apu_total[it]}", f_link, FMT_UF4)
            cell(wp, f"H{rr}", f"APU (hoja {apu_sheet_name(it)})", f_note)
        else:
            cell(wp, f"G{rr}", p.get("pu_uf"), f_inp, FMT_UF4, fill_inp)
            cell(wp, f"H{rr}", p.get("origen_pu", "Precio directo / cotización") if p else None,
                 f_warn if p and "EJEMPLO" in str(p.get("origen_pu", "")).upper() else f_note)
        cell(wp, f"I{rr}", f"=IF(AND(ISNUMBER(E{rr}),ISNUMBER(G{rr})),E{rr}*G{rr},0)", fmt=FMT_UF)
        cell(wp, f"J{rr}", f"=I{rr}*{UF}", fmt=FMT_CLP)
        cell(wp, f"K{rr}", f"=IF($I${pl+1}>0,I{rr}/$I${pl+1},0)", fmt=FMT_PCT)
        cell(wp, f"L{rr}", p.get("et"), f_inp, fill=fill_inp, align=Alignment(wrap_text=True))
    ptr = pl + 1
    cell(wp, f"C{ptr}", "COSTO DIRECTO TOTAL", f_bold, fill=fill_tot)
    for col in "ABDEFGHL":
        cell(wp, f"{col}{ptr}", None, fill=fill_tot)
    cell(wp, f"I{ptr}", f"=SUM(I{pf}:I{pl})", f_bold, FMT_UF, fill_tot)
    cell(wp, f"J{ptr}", f"=I{ptr}*{UF}", f_bold, FMT_CLP, fill_tot)
    cell(wp, f"K{ptr}", f"=SUM(K{pf}:K{pl})", f_bold, FMT_PCT, fill_tot)
    widths(wp, {"A": 8, "B": 26, "C": 46, "D": 8, "E": 13, "F": 15, "G": 13, "H": 26, "I": 14, "J": 16, "K": 11, "L": 40})
    wp.freeze_panes = "A5"
    P_CAP = f"'Partidas'!$B${pf}:$B${pl}"
    P_TOT = f"'Partidas'!$I${pf}:$I${pl}"
    REF_DIR = f"'Partidas'!$I${ptr}"

    # ---------------- Resumen ----------------
    wr = wb.create_sheet("Resumen")
    cell(wr, "B1", "Resumen de inversión por capítulo", f_tit, border=False)
    cell(wr, "B2", f"{d.get('proyecto', '')} · UF vigente:", f_bold, border=False)
    cell(wr, "D2", f"={UF}", f_link, '"$"#,##0.00', border=False)
    header(wr, 4, ["Capítulo", "Costo directo (UF)", "Costo directo (CLP)", "% del costo directo"], col0=2)
    caps = []
    for p in partidas:
        c = p.get("capitulo")
        if c and c not in caps:
            caps.append(c)
    rr = 5
    for c in caps:
        cell(wr, f"B{rr}", c)
        cell(wr, f"C{rr}", f'=SUMIF({P_CAP},B{rr},{P_TOT})', f_link, FMT_UF)
        cell(wr, f"D{rr}", f"=C{rr}*{UF}", fmt=FMT_CLP)
        cell(wr, f"E{rr}", f"=IF({REF_DIR}>0,C{rr}/{REF_DIR},0)", fmt=FMT_PCT)
        rr += 1
    cell(wr, f"B{rr}", "Costo directo total", f_bold, fill=fill_tot)
    cell(wr, f"C{rr}", f"={REF_DIR}", f_link_b, FMT_UF, fill_tot)
    cell(wr, f"D{rr}", f"=C{rr}*{UF}", f_bold, FMT_CLP, fill_tot)
    cell(wr, f"E{rr}", f"=SUM(E5:E{rr-1})", f_bold, FMT_PCT, fill_tot)
    cell(wr, f"B{rr+1}", "Control: suma de capítulos menos costo directo (debe ser 0; distinto de 0 = ítems sin capítulo)", f_note, border=False)
    cell(wr, f"E{rr+1}", f"=SUM(C5:C{rr-1})-C{rr}", f_note, FMT_UF, border=False)
    cell(wr, f"B{rr+3}", "Inversión total", f_sub, border=False)
    tot_r = resumen_recargos(wr, rr + 4, f"C{rr}", "Costo directo (itemizado)")
    cell(wr, f"B{tot_r+2}", "Incidencia por m² (si se ingresó la superficie en Parámetros C18)", f_note, border=False)
    cell(wr, f"D{tot_r+2}", f'=IF(N({SUP})>0,D{tot_r}/{SUP},"-")', f_bold, '#,##0.00" UF/m²"')
    cell(wr, f"B{tot_r+3}", "Contraste con la estimación paramétrica por m² (hoja Estimación m²)", f_note, border=False)
    cell(wr, f"D{tot_r+3}", f"={REF_PARAM}", f_link, FMT_UF)
    cell(wr, f"E{tot_r+3}", f'=IF({REF_PARAM}>0,D{tot_r}/{REF_PARAM}-1,"-")', f_note, '+0.0%;-0.0%;"-"')
    widths(wr, {"A": 2, "B": 44, "C": 34, "D": 20, "E": 18})

    # ---------------- Sensibilidad UF ----------------
    wsu = wb.create_sheet("Sensibilidad UF")
    cell(wsu, "A1", "Sensibilidad del total en pesos al valor de la UF", f_tit, border=False)
    cell(wsu, "A2", "El total en UF no cambia; el monto en pesos sí. Puede escribir otros valores de UF en la columna A.", f_note, border=False)
    cell(wsu, "A3", "Total inversión (UF)", f_bold)
    cell(wsu, "B3", f"='Resumen'!D{tot_r}" if detalle else f"={REF_PARAM}", f_link, FMT_UF)
    header(wsu, 5, ["Valor UF (CLP)", "Variación vs UF vigente", "Total (CLP)"])
    for i, s in enumerate([-0.05, -0.03, -0.01, 0, 0.01, 0.03, 0.05, 0.10]):
        r_ = 6 + i
        cell(wsu, f"A{r_}", f"=ROUND({UF}*(1+{s}),2)", f_inp, '"$"#,##0.00', fill_inp)
        cell(wsu, f"B{r_}", f"=A{r_}/{UF}-1", fmt='+0.0%;-0.0%;"-"')
        cell(wsu, f"C{r_}", f"=$B$3*A{r_}", f_bold if s == 0 else f_norm, FMT_CLP)
    widths(wsu, {"A": 24, "B": 24, "C": 24})

    # ---------------- Notas ----------------
    wn = wb.create_sheet("Notas")
    cell(wn, "A1", "Supuestos, fuentes y alcance", f_tit, border=False)
    base = [
        f"Documentos base de la cubicación: {d.get('documentos_base', '[indicar planos y especificaciones con su revisión]')}",
        f"Fuente UF: {d.get('fuente_uf', 'ingresada por el usuario')}.",
        f"Fuente costos unitarios por m²: {TABLA['fuente']}",
        "Los valores MINVU sirven para calcular derechos municipales y suelen quedar bajo el costo de mercado: "
        "se usan solo para contrastar el itemizado y para estimaciones de etapa temprana.",
        "Precios de insumos: netos, sin IVA, con su fuente y fecha en la hoja Insumos. Los marcados EJEMPLO deben reemplazarse por cotizaciones.",
        "Contingencia orientativa según nivel de definición (AACE 18R-97): perfil 25–30 %; conceptual 20–25 %; "
        "ingeniería básica 10–15 %; ingeniería de detalle 5–10 %.",
        "Excluye, salvo que se indique: terreno, permisos y derechos, mecánica de suelos, equipos de proceso, "
        "mobiliario, urbanización exterior y obras fuera del predio.",
        "Estimación de apoyo. La revisión y aprobación del monto corresponde al profesional responsable de JMS.",
    ]
    for i, t in enumerate(base + (d.get("notas") or [])):
        cell(wn, f"A{3 + i}", f"• {t}", f_norm, border=False, align=WRAP)
        wn.row_dimensions[3 + i].height = 30
    widths(wn, {"A": 130})

    # ---------------- orden de hojas ----------------
    orden = ["Parámetros", "Resumen", "Partidas", "Cubicación", "Insumos"] + [w.title for w in apu_sheets] + \
            ["Estimación m²", "Comparación materiales", "Tabla MINVU", "Sensibilidad UF", "Notas"]
    if not detalle:
        orden = ["Parámetros", "Estimación m²", "Comparación materiales", "Tabla MINVU", "Sensibilidad UF",
                 "Partidas", "Cubicación", "Insumos", "Resumen", "Notas"]
    wb._sheets = [wb[n] for n in orden]
    for w in wb.worksheets:
        w.sheet_view.showGridLines = False
    wb.active = 1
    wb.save(salida)
    print(f"OK: {salida}  ({len(partidas)} partidas, {len(cubic)} filas de cubicación, {len(apus)} APU, {len(insumos)} insumos)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
