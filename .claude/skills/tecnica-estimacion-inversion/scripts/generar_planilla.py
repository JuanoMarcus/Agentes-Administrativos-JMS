#!/usr/bin/env python3
"""Genera la planilla Excel de estimación de inversión JMS (UF y CLP, UF variable).

Uso:
    python3 generar_planilla.py entrada.json salida.xlsx

La entrada es un JSON con los datos del proyecto (ver ../assets/ejemplo_entrada.json).
Todos los cálculos quedan como fórmulas de Excel: al cambiar el valor de la UF,
los factores o los porcentajes en la hoja "Parámetros", todo se recalcula.
"""
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
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
f_note = Font(name=F, size=9, italic=True, color="595959")
fill_inp = PatternFill("solid", fgColor="FFFF00")
fill_head = PatternFill("solid", fgColor="D9DEE5")
fill_tot = PatternFill("solid", fgColor="EEF1F5")
thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
FMT_UF = '#,##0.00;(#,##0.00);"-"'
FMT_CLP = '"$"#,##0;("$"#,##0);"-"'
FMT_PCT = '0.0%;(0.0%);"-"'
FMT_M2 = '#,##0.0;(#,##0.0);"-"'
FMT_X = '0.00"x"'

P = "'Parámetros'"  # nombre de hoja con tilde: siempre entre comillas
UF = f"{P}!$C$5"
FR = f"{P}!$C$7"
FM = f"{P}!$C$8"
GG = f"{P}!$C$10"
UT = f"{P}!$C$11"
CO = f"{P}!$C$12"
HO = f"{P}!$C$13"
IV = f"{P}!$C$14"


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


def widths(ws, ws_widths):
    for col, w in ws_widths.items():
        ws.column_dimensions[col].width = w


def resumen_recargos(ws, row, ref_directo_uf, etiqueta="Costo directo"):
    """Escribe el bloque Costo directo → GG → Utilidades → Contingencia → Honorarios → Neto → IVA → Total.
    Columnas: B etiqueta, C base (texto), D UF, E CLP. Devuelve la fila del total."""
    header(ws, row, ["Concepto", "Base de cálculo", "Monto (UF)", "Monto (CLP)"], col0=2)
    r = row + 1
    filas = [
        (etiqueta, "Suma de recintos o partidas", f"={ref_directo_uf}"),
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


def main(entrada, salida):
    d = json.loads(Path(entrada).read_text(encoding="utf-8"))
    wb = Workbook()

    # ---------------- Parámetros ----------------
    ws = wb.active
    ws.title = "Parámetros"
    cell(ws, "B1", "Estimación de inversión — JMS Ingenieros Consultores", f_tit, border=False)
    cell(ws, "B2", f"{d.get('proyecto', '[Proyecto]')} · {d.get('mandante', '[Mandante]')} · {d.get('ubicacion', '[Ubicación]')}",
         f_sub, border=False)
    header(ws, 4, ["Parámetro", "Valor", "Nota / fuente"], col0=2)
    params = [
        (5, "Valor de la UF (CLP)", d["uf"], '"$"#,##0.00', d.get("fuente_uf", "Ingresado por el usuario")),
        (6, "Fecha del valor UF", d.get("fecha_uf", ""), None, "Fecha a la que corresponde el valor UF"),
        (7, "Factor regional", d.get("factor_regional", 1.0), FMT_X, d.get("nota_factor_regional", "1,00 = sin ajuste. Ajustar por zona (aislamiento, logística)")),
        (8, "Factor de mercado sobre tabla MINVU", d.get("factor_mercado", 1.0), FMT_X, d.get("nota_factor_mercado", "1,00 = valor oficial MINVU. Calibrar con presupuestos reales o cotizaciones")),
        (10, "Gastos generales", d.get("gastos_generales", 0.0), FMT_PCT, "% sobre costo directo"),
        (11, "Utilidades", d.get("utilidades", 0.0), FMT_PCT, "% sobre costo directo"),
        (12, "Contingencia", d.get("contingencia", 0.0), FMT_PCT, "Según nivel de definición (ver hoja Notas)"),
        (13, "Honorarios ingeniería / arquitectura", d.get("honorarios", 0.0), FMT_PCT, "% sobre subtotal construcción"),
        (14, "IVA", d.get("iva", 0.19), FMT_PCT, "Tasa general IVA Chile"),
    ]
    for r, lab, val, fmt, nota in params:
        cell(ws, f"B{r}", lab, f_bold)
        cell(ws, f"C{r}", val, f_inp, fmt, fill_inp)
        cell(ws, f"D{r}", nota, f_note, align=Alignment(wrap_text=True))
    cell(ws, "B9", "Recargos", f_sub, border=False)
    cell(ws, "B16", "Cómo usar esta planilla", f_sub, border=False)
    guia = [
        "Celdas con fondo amarillo y texto azul: datos que puede cambiar. Todo lo demás se calcula solo.",
        "Para actualizar los montos en pesos, cambie el valor de la UF en C5: todas las hojas se recalculan.",
        "Hoja Estimación: un recinto por fila (superficie, clase de material y categoría MINVU).",
        "Hoja Comparación materiales: misma superficie y categoría en hormigón armado, albañilería, acero y madera.",
        "Hoja Partidas: presupuesto detallado por cantidades, cuando el proyecto ya tiene cubicaciones.",
        "Hoja Sensibilidad UF: el total en pesos para distintos valores de la UF.",
        "Estimación referencial de orden de magnitud. No reemplaza un presupuesto con cubicaciones ni cotizaciones.",
    ]
    for i, t in enumerate(guia):
        cell(ws, f"B{17 + i}", f"• {t}", f_norm, border=False)
    widths(ws, {"A": 2, "B": 38, "C": 16, "D": 70})

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

    # ---------------- Estimación ----------------
    we = wb.create_sheet("Estimación")
    cell(we, "A1", "Estimación por superficie y material", f_tit, border=False)
    cell(we, "A2", "UF vigente:", f_bold, border=False)
    cell(we, "B2", f"={UF}", f_link, '"$"#,##0.00', border=False)
    cols = ["Recinto / edificación", "Superficie (m²)", "Clase", "Categoría", "Clave",
            "CLP/m² (tabla ajustada)", "UF/m² ajustado", "Subtotal (UF)", "Subtotal (CLP)"]
    header(we, 4, cols)
    recintos = d.get("recintos") or []
    n_rows = max(len(recintos) + 5, 12)
    first = 5
    last = first + n_rows - 1
    for i in range(n_rows):
        rr = first + i
        rec = recintos[i] if i < len(recintos) else {}
        cell(we, f"A{rr}", rec.get("descripcion"), f_inp, fill=fill_inp)
        cell(we, f"B{rr}", rec.get("superficie"), f_inp, FMT_M2, fill_inp)
        cell(we, f"C{rr}", rec.get("clase"), f_inp, fill=fill_inp, align=Alignment(horizontal="center"))
        cell(we, f"D{rr}", str(rec["categoria"]) if rec.get("categoria") is not None else None, f_inp,
             fill=fill_inp, align=Alignment(horizontal="center"))
        cell(we, f"E{rr}", f'=IF(C{rr}="","",C{rr}&"-"&D{rr})', align=Alignment(horizontal="center"))
        cell(we, f"F{rr}", f'=IF(E{rr}="","",IFERROR(INDEX({VAL},MATCH(E{rr},{KEY},0)),"sin valor"))', fmt=FMT_CLP)
        cell(we, f"G{rr}", f'=IF(ISNUMBER(F{rr}),F{rr}/{UF}*{FR}*{FM},"")', fmt=FMT_UF)
        cell(we, f"H{rr}", f'=IF(ISNUMBER(G{rr}),B{rr}*G{rr},0)', fmt=FMT_UF)
        cell(we, f"I{rr}", f"=H{rr}*{UF}", fmt=FMT_CLP)
    tr = last + 1
    cell(we, f"A{tr}", "Total", f_bold, fill=fill_tot)
    cell(we, f"B{tr}", f"=SUM(B{first}:B{last})", f_bold, FMT_M2, fill_tot)
    for col in "CDEFG":
        cell(we, f"{col}{tr}", None, fill=fill_tot)
    cell(we, f"H{tr}", f"=SUM(H{first}:H{last})", f_bold, FMT_UF, fill_tot)
    cell(we, f"I{tr}", f"=H{tr}*{UF}", f_bold, FMT_CLP, fill_tot)
    cell(we, f"A{tr + 1}", "Clase y categoría según hoja Tabla MINVU (edificación: categorías 1 a 5; galpones y bodegas: a, b, c). "
         "'sin valor' = combinación sin valor oficial.", f_note, border=False)
    dv_c = DataValidation(type="list", formula1='"' + ",".join(clases) + '"', allow_blank=True)
    dv_k = DataValidation(type="list", formula1='"1,2,3,4,5,a,b,c"', allow_blank=True)
    we.add_data_validation(dv_c)
    we.add_data_validation(dv_k)
    dv_c.add(f"C{first}:C{last}")
    dv_k.add(f"D{first}:D{last}")
    cell(we, f"A{tr + 3}", "Resumen de la inversión", f_sub, border=False)
    tot_e = resumen_recargos(we, tr + 4, f"H{tr}", "Costo directo (recintos)")
    if tot_e:
        cell(we, f"G{tot_e}", f"=IF(B{tr}>0,D{tot_e}/B{tr},0)", f_bold, '#,##0.00" UF/m²"', fill_tot)
        cell(we, f"G{tot_e - 1}", "Incidencia total", f_note, border=False)
    widths(we, {"A": 36, "B": 22, "C": 18, "D": 16, "E": 16, "F": 16, "G": 16, "H": 16, "I": 18})
    we.freeze_panes = "A5"

    # ---------------- Comparación materiales ----------------
    wc = wb.create_sheet("Comparación materiales")
    comp = d.get("comparar") or {}
    cell(wc, "A1", "Comparación por material estructural", f_tit, border=False)
    cell(wc, "A3", "Superficie (m²)", f_bold)
    cell(wc, "B3", comp.get("superficie", 1000), f_inp, FMT_M2, fill_inp)
    cell(wc, "A4", "Categoría de edificación (1 a 5)", f_bold)
    cell(wc, "B4", str(comp.get("categoria", 3)), f_inp, fill=fill_inp, align=Alignment(horizontal="center"))
    cell(wc, "A5", "Galpón o bodega: categoría (a, b, c)", f_bold)
    cell(wc, "B5", str(comp.get("categoria_galpon", "b")), f_inp, fill=fill_inp, align=Alignment(horizontal="center"))
    dv_e = DataValidation(type="list", formula1='"1,2,3,4,5"', allow_blank=False)
    dv_g = DataValidation(type="list", formula1='"a,b,c"', allow_blank=False)
    wc.add_data_validation(dv_e)
    wc.add_data_validation(dv_g)
    dv_e.add("B4")
    dv_g.add("B5")
    recargo = f"(1+{GG}+{UT})*(1+{CO}+{HO})*(1+{IV})"
    cell(wc, "D3", "Factor de recargos (GG, utilidades, contingencia, honorarios, IVA)", f_note, border=False)
    cell(wc, "D4", f"={recargo}", f_bold, FMT_X)
    header(wc, 7, ["Material", "Clase MINVU", "UF/m² directo", "Costo directo (UF)", "Total con recargos e IVA (UF)",
                   "Total con recargos e IVA (CLP)", "Diferencia vs hormigón armado"])
    mats = [
        ("Hormigón armado", "B", "B4"),
        ("Albañilería de ladrillo (armada o confinada)", "C", "B4"),
        ("Albañilería de bloques", "D", "B4"),
        ("Acero estructural", "A", "B4"),
        ("Madera", "E", "B4"),
        ("Acero galvanizado liviano (tipo Metalcon)", "G", "B4"),
        ("Galpón: estructura y cubierta de acero", "AA", "B5"),
        ("Galpón: estructura de hormigón, cubierta de acero", "BA", "B5"),
        ("Galpón: estructura de albañilería, cubierta de acero", "CA", "B5"),
        ("Galpón: estructura y cubierta de madera", "EE", "B5"),
    ]
    r0 = 8
    for i, (lab, cl, catref) in enumerate(mats):
        rr = r0 + i
        cell(wc, f"A{rr}", lab, f_bold if i in (0, 6) else f_norm)
        cell(wc, f"B{rr}", cl, align=Alignment(horizontal="center"))
        cell(wc, f"C{rr}", f'=IFERROR(INDEX({VAL},MATCH(B{rr}&"-"&${catref[0]}${catref[1:]},{KEY},0))/{UF}*{FR}*{FM},"sin valor")', fmt=FMT_UF)
        cell(wc, f"D{rr}", f'=IF(ISNUMBER(C{rr}),C{rr}*$B$3,"sin valor")', fmt=FMT_UF)
        cell(wc, f"E{rr}", f'=IF(ISNUMBER(D{rr}),D{rr}*$D$4,"sin valor")', fmt=FMT_UF)
        cell(wc, f"F{rr}", f'=IF(ISNUMBER(E{rr}),E{rr}*{UF},"sin valor")', fmt=FMT_CLP)
        base = f"$E${r0}" if i < 6 else f"$E${r0 + 6}"
        cell(wc, f"G{rr}", f'=IF(AND(ISNUMBER(E{rr}),ISNUMBER({base})),E{rr}/{base}-1,"")', fmt='+0.0%;-0.0%;"-"')
    cell(wc, f"A{r0 + len(mats) + 1}", "Filas 1 a 6: edificación (categoría en B4), diferencia respecto de hormigón armado. "
         "Filas 7 a 10: galpones y bodegas (categoría en B5), diferencia respecto del galpón de acero.", f_note, border=False)
    widths(wc, {"A": 50, "B": 14, "C": 16, "D": 20, "E": 24, "F": 26, "G": 22})

    # ---------------- Partidas ----------------
    wp = wb.create_sheet("Partidas")
    cell(wp, "A1", "Presupuesto detallado por partidas", f_tit, border=False)
    cell(wp, "A2", "Use esta hoja cuando existan cubicaciones. Precios unitarios en UF: de cotizaciones, APU o históricos JMS.", f_note, border=False)
    header(wp, 4, ["Ítem", "Capítulo", "Descripción", "Unidad", "Cantidad", "P.U. (UF)", "Total (UF)", "Total (CLP)", "Fuente del P.U."])
    partidas = d.get("partidas") or []
    caps = ["Obras preliminares e instalación de faenas", "Movimiento de tierras", "Fundaciones", "Estructura",
            "Cubierta y techumbre", "Cerramientos y tabiques", "Terminaciones", "Instalaciones sanitarias",
            "Instalaciones eléctricas", "Obras exteriores"]
    if not partidas:
        partidas = [{"item": f"{i + 1}.1", "capitulo": c} for i, c in enumerate(caps)]
    n_p = max(len(partidas) + 10, 25)
    pf, pl = 5, 5 + n_p - 1
    for i in range(n_p):
        rr = pf + i
        p = partidas[i] if i < len(partidas) else {}
        cell(wp, f"A{rr}", p.get("item"), f_inp, fill=fill_inp)
        cell(wp, f"B{rr}", p.get("capitulo"), f_inp, fill=fill_inp)
        cell(wp, f"C{rr}", p.get("descripcion"), f_inp, fill=fill_inp)
        cell(wp, f"D{rr}", p.get("unidad"), f_inp, fill=fill_inp, align=Alignment(horizontal="center"))
        cell(wp, f"E{rr}", p.get("cantidad"), f_inp, '#,##0.00;(#,##0.00);"-"', fill_inp)
        cell(wp, f"F{rr}", p.get("pu_uf"), f_inp, '#,##0.0000;(#,##0.0000);"-"', fill_inp)
        cell(wp, f"G{rr}", f"=IF(AND(ISNUMBER(E{rr}),ISNUMBER(F{rr})),E{rr}*F{rr},0)", fmt=FMT_UF)
        cell(wp, f"H{rr}", f"=G{rr}*{UF}", fmt=FMT_CLP)
        cell(wp, f"I{rr}", p.get("fuente"), f_inp, fill=fill_inp)
    ptr = pl + 1
    cell(wp, f"C{ptr}", "Costo directo partidas", f_bold, fill=fill_tot)
    cell(wp, f"G{ptr}", f"=SUM(G{pf}:G{pl})", f_bold, FMT_UF, fill_tot)
    cell(wp, f"H{ptr}", f"=G{ptr}*{UF}", f_bold, FMT_CLP, fill_tot)
    cell(wp, f"A{ptr + 2}", "Resumen de la inversión (partidas)", f_sub, border=False)
    resumen_recargos(wp, ptr + 3, f"G{ptr}", "Costo directo (partidas)")
    widths(wp, {"A": 8, "B": 34, "C": 44, "D": 30, "E": 16, "F": 14, "G": 16, "H": 18, "I": 30})
    wp.freeze_panes = "A5"

    # ---------------- Sensibilidad UF ----------------
    wsu = wb.create_sheet("Sensibilidad UF")
    cell(wsu, "A1", "Sensibilidad del total en pesos al valor de la UF", f_tit, border=False)
    cell(wsu, "A2", "El total en UF no cambia; el monto en pesos sí. Edite los valores de UF de la columna A.", f_note, border=False)
    cell(wsu, "A3", "Total estimación (UF)", f_bold)
    cell(wsu, "B3", f"='Estimación'!D{tot_e}", f_link, FMT_UF)
    header(wsu, 5, ["Valor UF (CLP)", "Variación vs UF vigente", "Total (CLP)"])
    pasos = [-0.05, -0.03, -0.01, 0, 0.01, 0.03, 0.05, 0.10]
    for i, s in enumerate(pasos):
        rr = 6 + i
        cell(wsu, f"A{rr}", f"=ROUND({UF}*(1+{s}),2)", f_inp, '"$"#,##0.00', fill_inp)
        cell(wsu, f"B{rr}", f"=A{rr}/{UF}-1", fmt='+0.0%;-0.0%;"-"')
        cell(wsu, f"C{rr}", f"=$B$3*A{rr}", f_bold if s == 0 else f_norm, FMT_CLP)
    widths(wsu, {"A": 24, "B": 24, "C": 24})

    # ---------------- Notas ----------------
    wn = wb.create_sheet("Notas")
    cell(wn, "A1", "Supuestos, fuentes y alcance", f_tit, border=False)
    notas = d.get("notas") or []
    base = [
        f"Fuente costos unitarios: {TABLA['fuente']}",
        "Los valores MINVU sirven para calcular derechos municipales de edificación; suelen quedar bajo el costo de mercado. "
        "El factor de mercado (Parámetros C8) permite calibrarlos con presupuestos o cotizaciones reales.",
        f"Fuente UF: {d.get('fuente_uf', 'ingresada por el usuario')}.",
        "Contingencia orientativa según nivel de definición (AACE 18R-97): perfil/conceptual 20–30 %; "
        "anteproyecto 15–20 %; ingeniería básica 10–15 %; ingeniería de detalle 5–10 %.",
        "Excluye, salvo que se indique: terreno, permisos y derechos, mecánica de suelos, equipos de proceso, "
        "mobiliario, urbanización exterior y obras fuera del predio.",
        "Estimación de apoyo. La revisión y aprobación del monto corresponde al ingeniero o profesional responsable de JMS.",
    ]
    for i, t in enumerate(base + notas):
        c = cell(wn, f"A{3 + i}", f"• {t}", f_norm, border=False, align=Alignment(wrap_text=True, vertical="top"))
        wn.row_dimensions[3 + i].height = 30
    widths(wn, {"A": 130})

    for w in wb.worksheets:
        w.sheet_view.showGridLines = False
    wb.save(salida)
    print(f"OK: {salida}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
