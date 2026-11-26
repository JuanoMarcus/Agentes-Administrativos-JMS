#!/usr/bin/env python3
"""Genera el Cuadro de Precios JMS (CDP) con APU, cubicación y bases de precios, en $ y UF.

Uso:
    python3 generar_planilla.py entrada.json salida.xlsx

Formato JMS (como CDP-001 Of. Proyecto CMPC Santa Fe):
  - CDP: encabezado de proyecto, ítems por capítulo y subcapítulo, Unid., Cant., P. Unit. y Total
    en $ y en UF, subtotales por capítulo, Costo directo, Gastos generales, Utilidades, Total neto, IVA y Total bruto.
  - APU (capítulo): un bloque por ítem con MATERIALES, MANO DE OBRA (HD, costo $/HD, LS %)
    y MAQ. Y EQUIPOS (costo, vida útil). Cantidades totales del ítem; rendimiento = cantidad / cantidad del presupuesto.
  - MATERIALES: base de precios de materiales, equipos y herramientas (proveedor y fecha).
  - Mano de obra: tarifas mensuales por especialidad; costo día = costo mes / 30.
  - Cubicación: memoria de cálculo por ítem con plano de origen.
  - Resumen por capítulo, estimación paramétrica por m² (tabla MINVU), sensibilidad a la UF, referencias y notas.

Cantidades y precios aceptan un número o una fórmula aritmética simple ("=2*7", "=341.6+286").
Al cambiar la UF (Parámetros C5), un precio, una tarifa o una medida, todo se recalcula.
"""
import json
import re
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
f_cap = Font(name=F, size=10, bold=True, color="1F2A44")
f_inp = Font(name=F, size=10, color="0000FF")
f_link = Font(name=F, size=10, color="008000")
f_link_b = Font(name=F, size=10, color="008000", bold=True)
f_note = Font(name=F, size=9, italic=True, color="595959")
f_warn = Font(name=F, size=9, italic=True, color="C00000")
fill_inp = PatternFill("solid", fgColor="FFFF00")
fill_head = PatternFill("solid", fgColor="D9DEE5")
fill_tot = PatternFill("solid", fgColor="EEF1F5")
fill_cap = PatternFill("solid", fgColor="E4E9F0")
thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
FMT_UF = '#,##0.00;(#,##0.00);"-"'
FMT_UF4 = '#,##0.0000;(#,##0.0000);"-"'
FMT_CLP = '"$"#,##0;("$"#,##0);"-"'
FMT_PCT = '0.0%;(0.0%);"-"'
FMT_Q = '#,##0.00;(#,##0.00);"-"'
FMT_Q4 = '#,##0.0000;(#,##0.0000);"-"'
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
IV = f"{P}!$C$13"
LS = f"{P}!$C$15"
SUP = f"{P}!$C$16"

RE_ARIT = re.compile(r"^=\+?[\d\s.,+\-*/()]+$")


def val(x):
    """Número o fórmula aritmética simple; cualquier otra fórmula se descarta (None)."""
    if isinstance(x, str) and x.startswith("="):
        return x.replace(",", ".") if RE_ARIT.match(x) else None
    return x


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


def header(ws, row, titles, col0=1, height=30):
    for i, t in enumerate(titles):
        cell(ws, f"{get_column_letter(col0 + i)}{row}", t, f_bold, fill=fill_head,
             align=Alignment(wrap_text=True, vertical="center", horizontal="center"))
    ws.row_dimensions[row].height = height


def widths(ws, ws_widths):
    for col, w in ws_widths.items():
        ws.column_dimensions[col].width = w


def qs(name):
    return "'" + name.replace("'", "''") + "'"


def safe_name(s, used):
    bad = '[]:*?/\\'
    s = "".join("-" if ch in bad else ch for ch in s)[:31]
    base, k = s, 2
    while s in used:
        s = (base[:28] + f" {k}")
        k += 1
    used.add(s)
    return s


def split_cod(txt):
    """'2.0 OBRA GRUESA' -> ('2.0', 'OBRA GRUESA')."""
    if not txt:
        return None, None
    parts = str(txt).split(" ", 1)
    if len(parts) == 2 and re.match(r"^[\d.,]+$", parts[0]):
        return parts[0], parts[1]
    return "", str(txt)


# =============================================================================
def main(entrada, salida):
    d = json.loads(Path(entrada).read_text(encoding="utf-8"))
    wb = Workbook()
    partidas = d.get("partidas") or []
    cubic = d.get("cubicacion") or []
    mats = d.get("materiales") or []
    mo = d.get("mano_obra") or []
    apus = d.get("apu") or {}
    used = set()

    # ---------------- Parámetros ----------------
    ws = wb.active
    ws.title = "Parámetros"
    used.add(ws.title)
    cell(ws, "B1", "Cuadro de precios y estimación de inversión — JMS Ingenieros Consultores", f_tit, border=False)
    cell(ws, "B2", f"{d.get('proyecto', '[Proyecto]')} · {d.get('mandante', '[Mandante]')}", f_sub, border=False)
    cell(ws, "B3", d.get("documentos_base", ""), f_note, border=False)
    header(ws, 4, ["Parámetro", "Valor", "Nota / fuente"], col0=2)
    params = [
        (5, "Valor de la UF ($)", d["uf"], '"$"#,##0.00', d.get("fuente_uf", "Ingresado por el usuario")),
        (6, "Fecha del valor UF", d.get("fecha_uf", ""), None, "Fecha a la que corresponde el valor UF"),
        (7, "Factor regional (estimación m²)", d.get("factor_regional", 1.0), FMT_X, "1,00 = sin ajuste"),
        (8, "Factor de mercado sobre tabla MINVU (estimación m²)", d.get("factor_mercado", 1.0), FMT_X,
         "1,00 = valor oficial MINVU. Calibrar con presupuestos reales"),
        (10, "Gastos generales", d.get("gastos_generales", 0.0), FMT_PCT, d.get("nota_gg", "% sobre costo directo")),
        (11, "Utilidades", d.get("utilidades", 0.0), FMT_PCT, d.get("nota_ut", "% sobre costo directo")),
        (12, "Imprevistos / contingencia", d.get("contingencia", 0.0), FMT_PCT, "% sobre costo directo (0 % si no se usa)"),
        (13, "IVA", d.get("iva", 0.19), FMT_PCT, "Tasa general IVA Chile"),
        (15, "Leyes sociales (LS) sobre mano de obra", d.get("leyes_sociales", 0.0), FMT_PCT,
         d.get("nota_ls", "Se aplica en todas las líneas de mano de obra de los APU")),
        (16, "Superficie construida (m²)", d.get("superficie_total"), '#,##0.0', "Para $/m² y UF/m²"),
    ]
    for r, lab, v, fmt, nota in params:
        cell(ws, f"B{r}", lab, f_bold)
        cell(ws, f"C{r}", v, f_inp, fmt, fill_inp)
        cell(ws, f"D{r}", nota, f_note, align=Alignment(wrap_text=True))
    cell(ws, "B9", "Recargos del cuadro de precios", f_sub, border=False)
    cell(ws, "B14", "Análisis de precios unitarios", f_sub, border=False)
    cell(ws, "B18", "Cómo usar esta planilla", f_sub, border=False)
    guia = [
        "Amarillo con texto azul: datos editables. Verde: vínculo a otra hoja. Negro: fórmula.",
        "Cambie la UF en C5: todas las columnas en UF se recalculan.",
        "CDP: cuadro de precios por capítulo. Cant. viene de Cubicación (o se ingresa); P. Unit. viene de su APU (o se ingresa).",
        "Hojas APU: un bloque por ítem. Cantidades totales del ítem; el rendimiento se calcula dividiendo por la cantidad del CDP.",
        "MATERIALES y Mano de obra: bases de precios. Un cambio de precio o tarifa actualiza todos los APU que la usan.",
        "Resumen: costo directo por capítulo, $/m² y UF/m². Estimación m² y Tabla MINVU: contraste paramétrico.",
        "Estimación de apoyo. La revisión y aprobación corresponde al profesional responsable de JMS.",
    ]
    for i, t in enumerate(guia):
        cell(ws, f"B{19 + i}", f"• {t}", f_norm, border=False)
    widths(ws, {"A": 2, "B": 46, "C": 16, "D": 80})

    # ---------------- MATERIALES (base) ----------------
    wm = wb.create_sheet("MATERIALES")
    used.add("MATERIALES")
    cell(wm, "A1", "BASE MATERIALES - EQUIPOS - HERRAMIENTAS", f_tit, border=False)
    cell(wm, "A2", "Precios netos en $ (sin IVA). Clave = código + correlativo. Indique proveedor y fecha de cada precio.", f_note, border=False)
    header(wm, 4, ["Categoría", "Código", "Correlativo", "Clave", "Descripción", "Unidad", "Precio ($)", "Precio (UF)",
                   "Rendimiento / nota", "Proveedor", "Fecha"])
    n_m = max(len(mats) + 20, 30)
    mf, ml = 5, 5 + n_m - 1
    for i in range(n_m):
        rr = mf + i
        m = mats[i] if i < len(mats) else {}
        cell(wm, f"A{rr}", m.get("categoria"), f_inp, fill=fill_inp)
        cell(wm, f"B{rr}", m.get("prefijo"), f_inp, fill=fill_inp, align=CENTER)
        cell(wm, f"C{rr}", m.get("correlativo"), f_inp, fill=fill_inp, align=CENTER)
        cell(wm, f"D{rr}", f'=IF(B{rr}="","",B{rr}&C{rr})', align=CENTER)
        cell(wm, f"E{rr}", m.get("descripcion"), f_inp, fill=fill_inp)
        cell(wm, f"F{rr}", m.get("unidad"), f_inp, fill=fill_inp, align=CENTER)
        cell(wm, f"G{rr}", val(m.get("precio")), f_inp, FMT_CLP, fill_inp)
        cell(wm, f"H{rr}", f'=IF(ISNUMBER(G{rr}),G{rr}/{UF},"")', fmt=FMT_UF4)
        cell(wm, f"I{rr}", m.get("rdto"), f_inp, fill=fill_inp)
        cell(wm, f"J{rr}", m.get("proveedor"), f_inp, fill=fill_inp)
        fe = m.get("fecha")
        cell(wm, f"K{rr}", fe, f_warn if fe and "EJEMPLO" in str(fe).upper() else f_inp, fill=fill_inp)
    widths(wm, {"A": 16, "B": 9, "C": 11, "D": 11, "E": 44, "F": 10, "G": 13, "H": 12, "I": 22, "J": 18, "K": 22})
    wm.freeze_panes = "A5"
    M_KEY = f"'MATERIALES'!$D${mf}:$D${ml}"
    M_DESC = f"'MATERIALES'!$E${mf}:$E${ml}"
    M_UNI = f"'MATERIALES'!$F${mf}:$F${ml}"
    M_PRE = f"'MATERIALES'!$G${mf}:$G${ml}"

    # ---------------- Mano de obra (tarifas) ----------------
    wmo = wb.create_sheet("Mano de obra")
    used.add("Mano de obra")
    cell(wmo, "A1", "Tarifas de mano de obra por especialidad", f_tit, border=False)
    cell(wmo, "A2", d.get("fuente_mano_obra", "Costo día = costo mensual empresa / 30. Indique la fuente de las tarifas."), f_note, border=False)
    header(wmo, 4, ["Especialidad", "$/mes líquido", "$/mes costo (base de cálculo)", "$/día (HD)", "$/día (UF)", "Fuente / fecha"])
    n_o = max(len(mo) + 8, 14)
    of_, ol = 5, 5 + n_o - 1
    for i in range(n_o):
        rr = of_ + i
        t = mo[i] if i < len(mo) else {}
        cell(wmo, f"A{rr}", t.get("especialidad"), f_inp, fill=fill_inp)
        cell(wmo, f"B{rr}", val(t.get("liquido_mes")), f_inp, FMT_CLP, fill_inp)
        cell(wmo, f"C{rr}", val(t.get("costo_mes")), f_inp, FMT_CLP, fill_inp)
        cell(wmo, f"D{rr}", f'=IF(ISNUMBER(C{rr}),C{rr}/30,"")', fmt=FMT_CLP)
        cell(wmo, f"E{rr}", f'=IF(ISNUMBER(D{rr}),D{rr}/{UF},"")', fmt=FMT_UF4)
        fu = t.get("fuente")
        cell(wmo, f"F{rr}", fu, f_warn if fu and "EJEMPLO" in str(fu).upper() else f_inp, fill=fill_inp)
    widths(wmo, {"A": 26, "B": 16, "C": 22, "D": 14, "E": 12, "F": 40})
    MO_ESP = f"'Mano de obra'!$A${of_}:$A${ol}"
    MO_DIA = f"'Mano de obra'!$D${of_}:$D${ol}"

    # ---------------- Plan de filas del CDP ----------------
    # filas: ("cap", cod, nombre) | ("sub", cod, nombre) | ("item", partida) | ("subtot", cap_idx)
    plan = []
    cap_actual = sub_actual = None
    caps = []
    for p in partidas:
        cap = p.get("capitulo") or "SIN CAPÍTULO"
        sub = p.get("subcapitulo")
        if cap != cap_actual:
            if cap_actual is not None:
                plan.append(("subtot", len(caps) - 1))
            caps.append(cap)
            plan.append(("cap",) + split_cod(cap))
            cap_actual, sub_actual = cap, None
        if sub and sub != sub_actual:
            plan.append(("sub",) + split_cod(sub))
            sub_actual = sub
        plan.append(("item", p))
    if caps:
        plan.append(("subtot", len(caps) - 1))
    CDP = "CDP"
    used.add(CDP)
    first_row = 11
    row_of_item = {}
    r = first_row
    for e in plan:
        if e[0] == "item":
            row_of_item[str(e[1].get("item"))] = r
        r += 1
        if e[0] == "subtot":
            r += 1  # fila en blanco tras cada capítulo
    last_plan_row = r - 1

    # ---------------- Cubicación ----------------
    wq = wb.create_sheet("Cubicación")
    used.add("Cubicación")
    cell(wq, "A1", "Memoria de cubicación", f_tit, border=False)
    cell(wq, "A2", "Cantidad parcial = N° veces × largo × ancho × alto (las medidas vacías no se multiplican), o la cantidad directa. "
         "Cada fila indica el plano o documento de origen.", f_note, border=False)
    header(wq, 4, ["Ítem", "Elemento / eje / ubicación", "Plano o documento de origen", "N° veces", "Largo (m)", "Ancho (m)",
                   "Alto o espesor (m)", "Cantidad directa", "Cantidad parcial", "Unid.", "Observaciones y supuestos"])
    n_q = max(len(cubic) + 30, 40)
    qf, ql = 5, 5 + n_q - 1
    for i in range(n_q):
        rr = qf + i
        q = cubic[i] if i < len(cubic) else {}
        cell(wq, f"A{rr}", str(q["item"]) if q.get("item") is not None else None, f_inp, fill=fill_inp, align=CENTER)
        cell(wq, f"B{rr}", q.get("elemento"), f_inp, fill=fill_inp)
        cell(wq, f"C{rr}", q.get("plano"), f_inp, fill=fill_inp)
        cell(wq, f"D{rr}", val(q.get("veces")), f_inp, FMT_Q, fill_inp)
        cell(wq, f"E{rr}", val(q.get("largo")), f_inp, '#,##0.000;(#,##0.000);"-"', fill_inp)
        cell(wq, f"F{rr}", val(q.get("ancho")), f_inp, '#,##0.000;(#,##0.000);"-"', fill_inp)
        cell(wq, f"G{rr}", val(q.get("alto")), f_inp, '#,##0.000;(#,##0.000);"-"', fill_inp)
        cell(wq, f"H{rr}", val(q.get("cantidad")), f_inp, FMT_Q, fill_inp)
        cell(wq, f"I{rr}", f'=IF(A{rr}="","",IF(ISNUMBER(H{rr}),H{rr},IF(COUNT(E{rr}:G{rr})=0,"",IF(ISNUMBER(D{rr}),D{rr},1)*PRODUCT(E{rr}:G{rr}))))', fmt=FMT_Q)
        cell(wq, f"J{rr}", f'=IF(A{rr}="","",IFERROR(INDEX({qs(CDP)}!$D${first_row}:$D${last_plan_row},MATCH(A{rr},{qs(CDP)}!$A${first_row}:$A${last_plan_row},0)),"ítem no existe"))', f_link, align=CENTER)
        cell(wq, f"K{rr}", q.get("obs"), f_inp, fill=fill_inp)
    widths(wq, {"A": 8, "B": 36, "C": 26, "D": 10, "E": 11, "F": 11, "G": 13, "H": 13, "I": 14, "J": 8, "K": 46})
    wq.freeze_panes = "A5"
    Q_ITEM = f"'Cubicación'!$A${qf}:$A${ql}"
    Q_CANT = f"'Cubicación'!$I${qf}:$I${ql}"
    cub_items = {str(q.get("item")) for q in cubic}

    # ---------------- APU por capítulo ----------------
    apu_pu = {}  # item -> ref a celda P.U. ($)
    apu_sheets = []
    items_por_cap = {}
    for p in partidas:
        it = str(p.get("item"))
        if it in apus:
            items_por_cap.setdefault(p.get("capitulo") or "SIN CAPÍTULO", []).append(p)
    for cap in caps:
        lista = items_por_cap.get(cap) or []
        if not lista:
            continue
        name = safe_name(f"APU ({lista[0]['item']}-{lista[-1]['item']})" if len(lista) > 1 else f"APU ({lista[0]['item']})", used)
        wa = wb.create_sheet(name)
        apu_sheets.append(wa)
        cell(wa, "B2", "APU (Resumido)", f_tit, border=False)
        cell(wa, "B3", cap, f_sub, border=False)
        r0 = 5
        for n, p in enumerate(lista, start=1):
            it = str(p["item"])
            a = apus[it]
            crow = row_of_item[it]
            cell(wa, f"A{r0}", "Ítem", f_bold, fill=fill_cap)
            cell(wa, f"B{r0}", f"={qs(CDP)}!A{crow}", f_link_b, fill=fill_cap)
            cell(wa, f"C{r0}", f"={qs(CDP)}!C{crow}", f_link_b, fill=fill_cap)
            for col in "DEFG":
                cell(wa, f"{col}{r0}", None, fill=fill_cap)
            cell(wa, f"H{r0}", n, f_note, fill=fill_cap, align=CENTER)
            cell(wa, f"B{r0+1}", "Cantidad Ppto.", f_bold)
            cell(wa, f"C{r0+1}", f"={qs(CDP)}!E{crow}", f_link, FMT_Q)
            cell(wa, f"D{r0+1}", f"={qs(CDP)}!D{crow}", f_link, align=CENTER)
            cell(wa, f"E{r0+1}", "Pre. Unit. ($)", f_bold)
            cell(wa, f"G{r0+1}", "Total Neto ($)", f_bold)
            cell(wa, f"E{r0+2}", "Pre. Unit. (UF)", f_bold)
            cell(wa, f"F{r0+2}", f"=F{r0+1}/{UF}", f_bold, FMT_UF4)
            cell(wa, f"G{r0+2}", "Total Neto (UF)", f_bold)
            cell(wa, f"H{r0+2}", f"=H{r0+1}/{UF}", f_bold, FMT_UF)
            QTY = f"$C${r0+1}"
            r = r0 + 3
            subtot = []
            # MATERIALES
            header(wa, r, ["Código", "MATERIALES", "Unidad", "Cantidad", "Rendto. (cant./unid.)", "Pérdida (%)", "Precio ($/un)", "Subtotal ($/unid.)"], height=28)
            lin = a.get("materiales") or []
            s0 = r + 1
            for k in range(len(lin) + 2):
                rr = s0 + k
                ln = lin[k] if k < len(lin) else {}
                cod = ln.get("codigo")
                cell(wa, f"A{rr}", cod, f_inp, fill=fill_inp, align=CENTER)
                if cod:
                    cell(wa, f"B{rr}", f'=IFERROR(INDEX({M_DESC},MATCH(A{rr},{M_KEY},0)),"código no existe")', f_link)
                    cell(wa, f"C{rr}", f'=IFERROR(INDEX({M_UNI},MATCH(A{rr},{M_KEY},0)),"")', f_link, align=CENTER)
                    cell(wa, f"G{rr}", f'=IFERROR(INDEX({M_PRE},MATCH(A{rr},{M_KEY},0)),0)', f_link, FMT_CLP)
                else:
                    cell(wa, f"B{rr}", ln.get("descripcion"), f_inp, fill=fill_inp)
                    cell(wa, f"C{rr}", ln.get("unidad"), f_inp, fill=fill_inp, align=CENTER)
                    cell(wa, f"G{rr}", val(ln.get("precio")), f_inp, FMT_CLP, fill_inp)
                cell(wa, f"D{rr}", val(ln.get("cantidad")), f_inp, FMT_Q4, fill_inp)
                cell(wa, f"E{rr}", f"=IF(N({QTY})>0,N(D{rr})/{QTY},0)", fmt=FMT_Q4)
                cell(wa, f"F{rr}", ln.get("perdida", 0) if ln else 0, f_inp, FMT_PCT, fill_inp)
                cell(wa, f"H{rr}", f"=E{rr}*(1+N(F{rr}))*N(G{rr})", fmt=FMT_CLP)
            s1 = s0 + len(lin) + 2
            cell(wa, f"G{s1}", "Subtotal materiales", f_note, border=False)
            cell(wa, f"H{s1}", f"=SUM(H{s0}:H{s1-1})", f_bold, FMT_CLP, fill_tot)
            subtot.append(f"H{s1}")
            # MANO DE OBRA
            r = s1 + 1
            header(wa, r, ["N°", "MANO DE OBRA", "Unidad", "Cantidad (HD)", "Rendto. (HD/unid.)", "Costo ($/HD)", "LS (%)", "Subtotal ($/unid.)"], height=28)
            lin = a.get("mano_obra") or []
            s0 = r + 1
            for k in range(len(lin) + 2):
                rr = s0 + k
                ln = lin[k] if k < len(lin) else {}
                cell(wa, f"A{rr}", k + 1 if ln else None, f_note, align=CENTER)
                cell(wa, f"B{rr}", ln.get("especialidad"), f_inp, fill=fill_inp)
                cell(wa, f"C{rr}", "HD" if ln else None, align=CENTER)
                cell(wa, f"D{rr}", val(ln.get("cantidad")), f_inp, FMT_Q4, fill_inp)
                cell(wa, f"E{rr}", f"=IF(N({QTY})>0,N(D{rr})/{QTY},0)", fmt=FMT_Q4)
                if ln.get("costo_hd") is not None:
                    cell(wa, f"F{rr}", val(ln.get("costo_hd")), f_inp, FMT_CLP, fill_inp)
                else:
                    cell(wa, f"F{rr}", f'=IF(B{rr}="",0,IFERROR(INDEX({MO_DIA},MATCH(B{rr},{MO_ESP},0)),0))', f_link, FMT_CLP)
                cell(wa, f"G{rr}", f"={LS}", f_link, FMT_PCT)
                cell(wa, f"H{rr}", f"=E{rr}*N(F{rr})*(1+G{rr})", fmt=FMT_CLP)
            s1 = s0 + len(lin) + 2
            cell(wa, f"G{s1}", "Subtotal mano de obra", f_note, border=False)
            cell(wa, f"H{s1}", f"=SUM(H{s0}:H{s1-1})", f_bold, FMT_CLP, fill_tot)
            subtot.append(f"H{s1}")
            # EQUIPOS
            r = s1 + 1
            header(wa, r, ["Código", "MAQ. Y EQUIPOS (SCTTO)", "Unidad", "Cantidad", "Rendto. (d/unid.)", "Costo ($)", "Vida útil (d)", "Subtotal ($/unid.)"], height=28)
            lin = a.get("equipos") or []
            s0 = r + 1
            for k in range(len(lin) + 2):
                rr = s0 + k
                ln = lin[k] if k < len(lin) else {}
                cod = ln.get("codigo")
                cell(wa, f"A{rr}", cod, f_inp, fill=fill_inp, align=CENTER)
                if cod:
                    cell(wa, f"B{rr}", f'=IFERROR(INDEX({M_DESC},MATCH(A{rr},{M_KEY},0)),"código no existe")', f_link)
                    cell(wa, f"C{rr}", f'=IFERROR(INDEX({M_UNI},MATCH(A{rr},{M_KEY},0)),"")', f_link, align=CENTER)
                    cell(wa, f"F{rr}", f'=IFERROR(INDEX({M_PRE},MATCH(A{rr},{M_KEY},0)),0)', f_link, FMT_CLP)
                else:
                    cell(wa, f"B{rr}", ln.get("descripcion"), f_inp, fill=fill_inp)
                    cell(wa, f"C{rr}", ln.get("unidad"), f_inp, fill=fill_inp, align=CENTER)
                    cell(wa, f"F{rr}", val(ln.get("costo")), f_inp, FMT_CLP, fill_inp)
                cell(wa, f"D{rr}", val(ln.get("cantidad")), f_inp, FMT_Q4, fill_inp)
                cell(wa, f"E{rr}", f"=IF(N({QTY})>0,N(D{rr})/{QTY},0)", fmt=FMT_Q4)
                cell(wa, f"G{rr}", ln.get("vida_util", 1) if ln else 365, f_inp, '#,##0', fill_inp)
                cell(wa, f"H{rr}", f"=IF(N(G{rr})>0,E{rr}*N(F{rr})/G{rr},0)", fmt=FMT_CLP)
            s1 = s0 + len(lin) + 2
            cell(wa, f"G{s1}", "Subtotal equipos", f_note, border=False)
            cell(wa, f"H{s1}", f"=SUM(H{s0}:H{s1-1})", f_bold, FMT_CLP, fill_tot)
            subtot.append(f"H{s1}")
            cell(wa, f"F{r0+1}", "=" + "+".join(subtot), f_bold, FMT_CLP, fill_tot)
            cell(wa, f"H{r0+1}", f"=F{r0+1}*C{r0+1}", f_bold, FMT_CLP, fill_tot)
            apu_pu[it] = f"{qs(name)}!$F${r0+1}"
            r0 = s1 + 3
        widths(wa, {"A": 9, "B": 42, "C": 9, "D": 13, "E": 14, "F": 14, "G": 14, "H": 16})

    # ---------------- CDP ----------------
    wc = wb.create_sheet(CDP)
    cell(wc, "B2", "CUADRO DE PRECIOS", f_tit, border=False)
    hdr = [("A3", "Cod.", "C3", d.get("codigo", "")), ("A4", "Fecha", "C4", d.get("fecha", "")),
           ("A5", "Rev.", "C5", d.get("revision", "")), ("A6", "Superf.", "C6", f"={SUP}"),
           ("E3", "Proyecto", "F3", d.get("proyecto", "")), ("E4", "Mandante", "F4", d.get("mandante", "")),
           ("E5", "Dirección", "F5", d.get("direccion", "")), ("E6", "E-mail", "F6", d.get("email", "")),
           ("E7", "Contacto", "F7", d.get("contacto", "")), ("J3", "Valor UF", "K3", f"={UF}"),
           ("J4", "Fecha UF", "K4", f"={P}!C6")]
    for lab_ref, lab, v_ref, v in hdr:
        cell(wc, lab_ref, lab, f_bold, border=False)
        cell(wc, v_ref, v, f_link if isinstance(v, str) and v.startswith("=") else f_norm, border=False,
             align=Alignment(horizontal="left"))
    wc["K3"].number_format = '"$"#,##0.00'
    wc["C6"].number_format = '#,##0.0" m²"'
    header(wc, 10, ["Ítem", "Descripción", "", "Unid.", "Cant.", "P. Unit. ($)", "Total ($)", "P. Unit. (UF)", "Total (UF)",
                    "Origen cantidad", "Origen P. Unit.", "Especificación técnica"])
    wc.merge_cells("B10:C10")
    r = first_row
    cap_rows = {}  # idx -> (primera fila ítems, fila subtotal)
    cap_start = None
    cap_idx = -1
    for e in plan:
        if e[0] == "cap":
            cap_idx += 1
            cell(wc, f"A{r}", e[1], f_cap, fill=fill_cap)
            cell(wc, f"B{r}", e[2], f_cap, fill=fill_cap)
            for col in "CDEFGHIJKL":
                cell(wc, f"{col}{r}", None, fill=fill_cap)
            cap_start = r + 1
        elif e[0] == "sub":
            cell(wc, f"A{r}", e[1], f_bold)
            cell(wc, f"B{r}", e[2], f_bold)
        elif e[0] == "item":
            p = e[1]
            it = str(p["item"])
            cell(wc, f"A{r}", it, align=Alignment(horizontal="left"))
            cell(wc, f"C{r}", p.get("descripcion"), f_inp, fill=fill_inp, align=Alignment(wrap_text=True))
            cell(wc, f"D{r}", p.get("unidad"), f_inp, fill=fill_inp, align=CENTER)
            if it in cub_items:
                cell(wc, f"E{r}", f"=SUMIF({Q_ITEM},A{r},{Q_CANT})", f_link, FMT_Q)
                cell(wc, f"J{r}", "Cubicación", f_note)
            else:
                cell(wc, f"E{r}", val(p.get("cantidad")), f_inp, FMT_Q, fill_inp)
                cell(wc, f"J{r}", p.get("origen_cantidad", "Ingresada en el cuadro"), f_note)
            if p.get("por_mandante"):
                cell(wc, f"F{r}", p["por_mandante"], f_note, align=CENTER)
                cell(wc, f"K{r}", "Por cuenta del mandante", f_note)
            elif it in apu_pu:
                cell(wc, f"F{r}", f"={apu_pu[it]}", f_link, FMT_CLP)
                cell(wc, f"K{r}", "APU", f_note)
            else:
                pu = val(p.get("pu"))
                if pu is None and p.get("pu_uf") is not None:
                    pu = f"={p['pu_uf']}*{UF}"
                cell(wc, f"F{r}", pu, f_inp, FMT_CLP, fill_inp)
                o = p.get("origen_pu", "Precio directo / cotización")
                cell(wc, f"K{r}", o, f_warn if "EJEMPLO" in str(o).upper() else f_note)
            cell(wc, f"G{r}", f"=IF(AND(ISNUMBER(E{r}),ISNUMBER(F{r})),E{r}*F{r},0)", fmt=FMT_CLP)
            cell(wc, f"H{r}", f'=IF(ISNUMBER(F{r}),F{r}/{UF},"")', fmt=FMT_UF4)
            cell(wc, f"I{r}", f"=G{r}/{UF}", fmt=FMT_UF)
            cell(wc, f"L{r}", p.get("et"), f_inp, fill=fill_inp, align=Alignment(wrap_text=True))
            cell(wc, f"B{r}", None)
        elif e[0] == "subtot":
            cell(wc, f"C{r}", f"Subtotal {caps[e[1]]}", f_bold, fill=fill_tot)
            for col in "ABDEFHJKL":
                cell(wc, f"{col}{r}", None, fill=fill_tot)
            cell(wc, f"G{r}", f"=SUM(G{cap_start}:G{r-1})", f_bold, FMT_CLP, fill_tot)
            cell(wc, f"I{r}", f"=G{r}/{UF}", f_bold, FMT_UF, fill_tot)
            cap_rows[e[1]] = (cap_start, r)
            r += 1
        r += 1
    r += 1
    sub_refs = "+".join(f"G{v[1]}" for v in cap_rows.values()) or "0"
    cd = r
    filas_fin = [
        (cd, "COSTO DIRECTO", None, None, f"={sub_refs}"),
        (cd + 1, "GASTOS GENERALES", "%", f"={GG}", f"=E{cd+1}*G{cd}"),
        (cd + 2, "UTILIDADES", "%", f"={UT}", f"=E{cd+2}*G{cd}"),
        (cd + 3, "IMPREVISTOS", "%", f"={CO}", f"=E{cd+3}*G{cd}"),
        (cd + 4, "TOTAL NETO", None, None, f"=SUM(G{cd}:G{cd+3})"),
        (cd + 5, "IVA", "%", f"={IV}", f"=E{cd+5}*G{cd+4}"),
        (cd + 6, "TOTAL BRUTO", None, None, f"=G{cd+4}+G{cd+5}"),
    ]
    for rr, lab, unid, pct, fml in filas_fin:
        bold = lab in ("COSTO DIRECTO", "TOTAL NETO", "TOTAL BRUTO")
        fill = fill_tot if bold else None
        cell(wc, f"B{rr}", lab, f_bold if bold else f_norm, fill=fill)
        cell(wc, f"C{rr}", None, fill=fill)
        cell(wc, f"D{rr}", unid, fill=fill, align=CENTER)
        cell(wc, f"E{rr}", pct, f_link, FMT_PCT, fill)
        cell(wc, f"F{rr}", f"=G{cd}" if unid and lab != "IVA" else (f"=G{cd+4}" if lab == "IVA" else None), fmt=FMT_CLP, fill=fill)
        cell(wc, f"G{rr}", fml, f_bold if bold else f_norm, FMT_CLP, fill)
        cell(wc, f"H{rr}", None, fill=fill)
        cell(wc, f"I{rr}", f"=G{rr}/{UF}", f_bold if bold else f_norm, FMT_UF, fill)
    tn, tb = cd + 4, cd + 6
    cell(wc, "A7", "Presup.", f_bold, border=False)
    cell(wc, "C7", f"=G{tn}", f_bold, FMT_CLP + "", border=False, align=Alignment(horizontal="left"))
    cell(wc, "J5", "Total neto (UF)", f_bold, border=False)
    cell(wc, "K5", f"=I{tn}", f_bold, FMT_UF, border=False, align=Alignment(horizontal="left"))
    cell(wc, "J6", "UF/m² (neto)", f_bold, border=False)
    cell(wc, "K6", f'=IF(N({SUP})>0,I{tn}/{SUP},"-")', f_bold, '#,##0.00', border=False, align=Alignment(horizontal="left"))
    obs = d.get("observaciones") or []
    cell(wc, f"A{tb + 3}", "OBSERVACIONES:", f_bold, border=False)
    for i, t in enumerate(obs):
        cell(wc, f"B{tb + 4 + i}", f"{i + 1}. {t}", f_norm, border=False)
    cell(wc, f"F{tb + 6 + len(obs)}", d.get("firma", "JMS Ingenieros Consultores Ltda."), f_bold, border=False)
    widths(wc, {"A": 8, "B": 4, "C": 50, "D": 7, "E": 12, "F": 15, "G": 17, "H": 12, "I": 13, "J": 15, "K": 22, "L": 34})
    wc.freeze_panes = "A11"

    # ---------------- Resumen ----------------
    wr = wb.create_sheet("Resumen")
    cell(wr, "C2", "RESUMEN POR CAPÍTULO", f_tit, border=False)
    cell(wr, "C4", "Valor UF", f_bold, border=False)
    cell(wr, "D4", f"={UF}", f_link, '"$"#,##0.00', border=False)
    cell(wr, "C5", "Fecha UF", f_bold, border=False)
    cell(wr, "D5", f"={P}!C6", f_link, border=False)
    cell(wr, "F4", "Superficie (m²)", f_bold, border=False)
    cell(wr, "G4", f"={SUP}", f_link, '#,##0.0', border=False)
    header(wr, 6, ["Capítulo", "% del directo", "Directo ($)", "Directo (UF)", "$/m²", "UF/m²"], col0=3)
    rr = 7
    for idx, cap in enumerate(caps):
        st = cap_rows[idx][1]
        cell(wr, f"C{rr}", cap)
        cell(wr, f"D{rr}", f"=IF({qs(CDP)}!$G${cd}>0,E{rr}/{qs(CDP)}!$G${cd},0)", fmt=FMT_PCT)
        cell(wr, f"E{rr}", f"={qs(CDP)}!G{st}", f_link, FMT_CLP)
        cell(wr, f"F{rr}", f"=E{rr}/{UF}", fmt=FMT_UF)
        cell(wr, f"G{rr}", f'=IF(N({SUP})>0,E{rr}/{SUP},"-")', fmt=FMT_CLP)
        cell(wr, f"H{rr}", f'=IF(N({SUP})>0,F{rr}/{SUP},"-")', fmt=FMT_UF)
        rr += 1
    resumen = [("COSTO DIRECTO", cd), ("GASTOS GENERALES", cd + 1), ("UTILIDADES", cd + 2), ("IMPREVISTOS", cd + 3),
               ("TOTAL NETO", cd + 4), ("IVA", cd + 5), ("TOTAL BRUTO", cd + 6)]
    for lab, src in resumen:
        bold = lab in ("COSTO DIRECTO", "TOTAL NETO", "TOTAL BRUTO")
        fill = fill_tot if bold else None
        cell(wr, f"C{rr}", lab, f_bold if bold else f_norm, fill=fill)
        cell(wr, f"D{rr}", f"={qs(CDP)}!E{src}" if src not in (cd, cd + 4, cd + 6) else None, f_link, FMT_PCT, fill)
        cell(wr, f"E{rr}", f"={qs(CDP)}!G{src}", f_link_b if bold else f_link, FMT_CLP, fill)
        cell(wr, f"F{rr}", f"=E{rr}/{UF}", f_bold if bold else f_norm, FMT_UF, fill)
        cell(wr, f"G{rr}", f'=IF(N({SUP})>0,E{rr}/{SUP},"-")', f_bold if bold else f_norm, FMT_CLP, fill)
        cell(wr, f"H{rr}", f'=IF(N({SUP})>0,F{rr}/{SUP},"-")', f_bold if bold else f_norm, FMT_UF, fill)
        if lab == "TOTAL NETO":
            neto_row = rr
        rr += 1
    var = d.get("variacion", 0.20)
    cell(wr, f"C{rr+1}", f"Rango del total neto (±{int(var*100)} %)", f_bold, border=False)
    cell(wr, f"C{rr+2}", "Mínimo", f_norm)
    cell(wr, f"E{rr+2}", f"=E{neto_row}*(1-{var})", fmt=FMT_CLP)
    cell(wr, f"F{rr+2}", f"=F{neto_row}*(1-{var})", fmt=FMT_UF)
    cell(wr, f"H{rr+2}", f'=IF(N({SUP})>0,F{rr+2}/{SUP},"-")', fmt=FMT_UF)
    cell(wr, f"C{rr+3}", "Máximo", f_norm)
    cell(wr, f"E{rr+3}", f"=E{neto_row}*(1+{var})", fmt=FMT_CLP)
    cell(wr, f"F{rr+3}", f"=F{neto_row}*(1+{var})", fmt=FMT_UF)
    cell(wr, f"H{rr+3}", f'=IF(N({SUP})>0,F{rr+3}/{SUP},"-")', fmt=FMT_UF)
    widths(wr, {"A": 2, "B": 2, "C": 46, "D": 13, "E": 18, "F": 14, "G": 14, "H": 12})
    REF_NETO = f"'Resumen'!$F${neto_row}"

    # ---------------- Estimación m² (paramétrica) ----------------
    wt = wb.create_sheet("Tabla MINVU")
    cell(wt, "A1", "Costos unitarios por m² de construcción — MINVU", f_tit, border=False)
    cell(wt, "A2", TABLA["fuente"], f_note, border=False)
    header(wt, 4, ["Clave", "Clase", "Material / estructura", "Categoría", "Calidad", "$/m² (oficial)",
                   "Factor de ajuste por clase", "$/m² ajustado", "UF/m² ajustado"])
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
        cell(wt, f"H{r}", f"=F{r}*G{r}", fmt=FMT_CLP)
        cell(wt, f"I{r}", f"=H{r}/{UF}", fmt=FMT_UF)
        r += 1
    t_last = r - 1
    cell(wt, f"A{r + 1}", TABLA["nota"], f_note, border=False)
    cell(wt, f"A{r + 2}", "Valores oficiales para derechos municipales, no de mercado. Acero (A) y albañilería (C, D) tienen el mismo valor: "
         "use el factor por clase para diferenciarlos con presupuestos reales de JMS.", f_note, border=False)
    widths(wt, {"A": 9, "B": 7, "C": 48, "D": 10, "E": 22, "F": 14, "G": 14, "H": 14, "I": 14})
    KEY = f"'Tabla MINVU'!$A$5:$A${t_last}"
    VALT = f"'Tabla MINVU'!$H$5:$H${t_last}"
    clases = sorted({f["clase"] for f in TABLA["filas"]}, key=lambda c: (len(c), c))

    we = wb.create_sheet("Estimación m²")
    cell(we, "A1", "Estimación paramétrica por superficie y material (contraste)", f_tit, border=False)
    header(we, 4, ["Recinto / edificación", "Superficie (m²)", "Clase", "Categoría", "Clave", "$/m² (tabla ajustada)",
                   "UF/m² ajustado", "Subtotal (UF)", "Subtotal ($)"])
    recintos = d.get("recintos") or []
    n_rows = max(len(recintos) + 4, 8)
    first, last = 5, 5 + n_rows - 1
    for i in range(n_rows):
        rr = first + i
        rec = recintos[i] if i < len(recintos) else {}
        cell(we, f"A{rr}", rec.get("descripcion"), f_inp, fill=fill_inp)
        cell(we, f"B{rr}", rec.get("superficie"), f_inp, '#,##0.0;(#,##0.0);"-"', fill_inp)
        cell(we, f"C{rr}", rec.get("clase"), f_inp, fill=fill_inp, align=CENTER)
        cell(we, f"D{rr}", str(rec["categoria"]) if rec.get("categoria") is not None else None, f_inp, fill=fill_inp, align=CENTER)
        cell(we, f"E{rr}", f'=IF(C{rr}="","",C{rr}&"-"&D{rr})', align=CENTER)
        cell(we, f"F{rr}", f'=IF(E{rr}="","",IFERROR(INDEX({VALT},MATCH(E{rr},{KEY},0)),"sin valor"))', fmt=FMT_CLP)
        cell(we, f"G{rr}", f'=IF(ISNUMBER(F{rr}),F{rr}/{UF}*{FR}*{FM},"")', fmt=FMT_UF)
        cell(we, f"H{rr}", f'=IF(ISNUMBER(G{rr}),B{rr}*G{rr},0)', fmt=FMT_UF)
        cell(we, f"I{rr}", f"=H{rr}*{UF}", fmt=FMT_CLP)
    tr = last + 1
    cell(we, f"A{tr}", "Costo directo paramétrico", f_bold, fill=fill_tot)
    cell(we, f"B{tr}", f"=SUM(B{first}:B{last})", f_bold, '#,##0.0', fill_tot)
    cell(we, f"H{tr}", f"=SUM(H{first}:H{last})", f_bold, FMT_UF, fill_tot)
    cell(we, f"I{tr}", f"=H{tr}*{UF}", f_bold, FMT_CLP, fill_tot)
    cell(we, f"A{tr+1}", "Neto paramétrico (con GG, utilidades e imprevistos)", f_bold)
    cell(we, f"H{tr+1}", f"=H{tr}*(1+{GG}+{UT}+{CO})", f_bold, FMT_UF)
    cell(we, f"A{tr+2}", "Diferencia del CDP (neto) respecto del paramétrico", f_note, border=False)
    cell(we, f"H{tr+2}", f'=IF(H{tr+1}>0,{REF_NETO}/H{tr+1}-1,"-")', f_note, '+0.0%;-0.0%;"-"', border=False)
    dv_c = DataValidation(type="list", formula1='"' + ",".join(clases) + '"', allow_blank=True)
    dv_k = DataValidation(type="list", formula1='"1,2,3,4,5,a,b,c"', allow_blank=True)
    we.add_data_validation(dv_c)
    we.add_data_validation(dv_k)
    dv_c.add(f"C{first}:C{last}")
    dv_k.add(f"D{first}:D{last}")
    widths(we, {"A": 44, "B": 14, "C": 9, "D": 10, "E": 9, "F": 18, "G": 14, "H": 14, "I": 16})

    wcm = wb.create_sheet("Comparación materiales")
    comp = d.get("comparar") or {}
    cell(wcm, "A1", "Comparación por material estructural (paramétrica)", f_tit, border=False)
    cell(wcm, "A3", "Superficie (m²)", f_bold)
    cell(wcm, "B3", comp.get("superficie", d.get("superficie_total") or 1000), f_inp, '#,##0.0', fill_inp)
    cell(wcm, "A4", "Categoría de edificación (1 a 5)", f_bold)
    cell(wcm, "B4", str(comp.get("categoria", 3)), f_inp, fill=fill_inp, align=CENTER)
    cell(wcm, "A5", "Galpón o bodega (a, b, c)", f_bold)
    cell(wcm, "B5", str(comp.get("categoria_galpon", "b")), f_inp, fill=fill_inp, align=CENTER)
    cell(wcm, "D4", f"=(1+{GG}+{UT}+{CO})*(1+{IV})", f_bold, FMT_X)
    cell(wcm, "D3", "Factor de recargos e IVA", f_note, border=False)
    header(wcm, 7, ["Material", "Clase", "UF/m² directo", "Directo (UF)", "Total bruto (UF)", "Total bruto ($)", "Diferencia vs referencia"])
    lst = [("Hormigón armado", "B", "B4"), ("Albañilería de ladrillo (armada o confinada)", "C", "B4"),
           ("Albañilería de bloques", "D", "B4"), ("Acero estructural", "A", "B4"), ("Madera", "E", "B4"),
           ("Acero galvanizado liviano (tipo Metalcon)", "G", "B4"), ("Galpón: estructura y cubierta de acero", "AA", "B5"),
           ("Galpón: estructura de hormigón, cubierta de acero", "BA", "B5"),
           ("Galpón: estructura de albañilería, cubierta de acero", "CA", "B5"), ("Galpón: estructura y cubierta de madera", "EE", "B5")]
    for i, (lab, cl, cref) in enumerate(lst):
        rr = 8 + i
        cell(wcm, f"A{rr}", lab, f_bold if i in (0, 6) else f_norm)
        cell(wcm, f"B{rr}", cl, align=CENTER)
        cell(wcm, f"C{rr}", f'=IFERROR(INDEX({VALT},MATCH(B{rr}&"-"&${cref[0]}${cref[1:]},{KEY},0))/{UF}*{FR}*{FM},"sin valor")', fmt=FMT_UF)
        cell(wcm, f"D{rr}", f'=IF(ISNUMBER(C{rr}),C{rr}*$B$3,"sin valor")', fmt=FMT_UF)
        cell(wcm, f"E{rr}", f'=IF(ISNUMBER(D{rr}),D{rr}*$D$4,"sin valor")', fmt=FMT_UF)
        cell(wcm, f"F{rr}", f'=IF(ISNUMBER(E{rr}),E{rr}*{UF},"sin valor")', fmt=FMT_CLP)
        base = "$E$8" if i < 6 else "$E$14"
        cell(wcm, f"G{rr}", f'=IF(AND(ISNUMBER(E{rr}),ISNUMBER({base})),E{rr}/{base}-1,"")', fmt='+0.0%;-0.0%;"-"')
    widths(wcm, {"A": 50, "B": 9, "C": 14, "D": 16, "E": 18, "F": 20, "G": 20})

    # ---------------- Sensibilidad UF ----------------
    wsu = wb.create_sheet("Sensibilidad UF")
    cell(wsu, "A1", "Sensibilidad del total en pesos al valor de la UF", f_tit, border=False)
    cell(wsu, "A2", "El total en UF no cambia; el monto en pesos sí. Puede escribir otros valores de UF en la columna A.", f_note, border=False)
    cell(wsu, "A3", "Total neto (UF)", f_bold)
    cell(wsu, "B3", f"={REF_NETO}", f_link, FMT_UF)
    header(wsu, 5, ["Valor UF ($)", "Variación vs UF vigente", "Total neto ($)", "Total bruto con IVA ($)"])
    for i, s in enumerate([-0.05, -0.03, -0.01, 0, 0.01, 0.03, 0.05, 0.10]):
        r_ = 6 + i
        cell(wsu, f"A{r_}", f"=ROUND({UF}*(1+{s}),2)", f_inp, '"$"#,##0.00', fill_inp)
        cell(wsu, f"B{r_}", f"=A{r_}/{UF}-1", fmt='+0.0%;-0.0%;"-"')
        cell(wsu, f"C{r_}", f"=$B$3*A{r_}", f_bold if s == 0 else f_norm, FMT_CLP)
        cell(wsu, f"D{r_}", f"=C{r_}*(1+{IV})", fmt=FMT_CLP)
    widths(wsu, {"A": 20, "B": 22, "C": 22, "D": 24})

    # ---------------- Referencias y Notas ----------------
    wf = wb.create_sheet("Referencias")
    cell(wf, "A1", "Referencias de precios y rendimientos", f_tit, border=False)
    refs = d.get("referencias") or []
    for i, ref in enumerate(refs):
        cell(wf, f"A{3 + i}", ref.get("nombre"), f_bold, border=False)
        cell(wf, f"B{3 + i}", ref.get("url"), f_norm, border=False)
    widths(wf, {"A": 36, "B": 70})

    wn = wb.create_sheet("Notas")
    cell(wn, "A1", "Supuestos, fuentes y alcance", f_tit, border=False)
    base = [
        f"Documentos base: {d.get('documentos_base', '[indicar planos y especificaciones con su revisión]')}",
        f"Fuente UF: {d.get('fuente_uf', 'ingresada por el usuario')}.",
        f"Estimación paramétrica: {TABLA['fuente']}",
        "Precios netos (sin IVA), con proveedor y fecha en MATERIALES y Mano de obra. Los marcados EJEMPLO deben reemplazarse.",
        "En los APU, las cantidades son totales del ítem y el rendimiento = cantidad / cantidad del cuadro de precios. "
        "Equipos: costo / vida útil (1 = arriendo por día; 365 = herramienta propia).",
        "Excluye, salvo que se indique: terreno, permisos y derechos, estudios no indicados, equipos de proceso y obras fuera del predio.",
        "Estimación de apoyo. La revisión y aprobación del monto corresponde al profesional responsable de JMS.",
    ]
    for i, t in enumerate(base + (d.get("notas") or [])):
        cell(wn, f"A{3 + i}", f"• {t}", f_norm, border=False, align=WRAP)
        wn.row_dimensions[3 + i].height = 30
    widths(wn, {"A": 130})

    orden = ["Parámetros", CDP, "Resumen", "Cubicación"] + [w.title for w in apu_sheets] + \
            ["MATERIALES", "Mano de obra", "Estimación m²", "Comparación materiales", "Tabla MINVU",
             "Sensibilidad UF", "Referencias", "Notas"]
    wb._sheets = [wb[n] for n in orden]
    for w in wb.worksheets:
        w.sheet_view.showGridLines = False
    wb.active = 1
    wb.save(salida)
    print(f"OK: {salida}  ({len(partidas)} partidas en {len(caps)} capítulos, {len(apus)} APU, "
          f"{len(cubic)} filas de cubicación, {len(mats)} materiales, {len(mo)} tarifas)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
