#!/usr/bin/env python3
"""Convierte un Cuadro de Precios JMS existente (CDP + hojas APU + MATERIALES) en JSON reutilizable.

Uso:
    python3 extraer_cdp.py cuadro.xlsx salida.json [--hoja-cdp CDP-001]

El JSON resultante sirve como:
  - base histórica de APU, rendimientos y precios para nuevos proyectos (buscar ítems parecidos);
  - entrada directa para generar_planilla.py (reconstruye el cuadro con columnas en UF).

Lee: ítems (capítulo, subcapítulo, ítem, descripción, unidad, cantidad, P. Unit.), bloques APU
(materiales, mano de obra, equipos, con sus cantidades y precios), base MATERIALES, tarifas de mano
de obra (tabla lateral de las hojas APU) y referencias. Las cantidades escritas como fórmula
aritmética (=341.6+286) se conservan como fórmula; las que dependen de otras celdas, como valor.
"""
import argparse
import json
import re
from datetime import date, datetime

from openpyxl import load_workbook

RE_ARIT = re.compile(r"^=\+?[\d\s.+\-*/()]+$")
RE_REF = re.compile(r"'?([^'!]+)'?!\$?([A-Z]+)\$?(\d+)")


def num_o_formula(f, v):
    if isinstance(f, str) and f.startswith("=") and RE_ARIT.match(f):
        return f.replace("=+", "=")
    return v if isinstance(v, (int, float)) else None


def txt(v):
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    return None if v is None else str(v).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("salida")
    ap.add_argument("--hoja-cdp")
    a = ap.parse_args()
    wf = load_workbook(a.xlsx)                  # fórmulas
    wv = load_workbook(a.xlsx, data_only=True)  # valores

    # --- hoja CDP: la que tenga "CUADRO DE PRECIOS" y más filas de ítems, o la indicada ---
    cands = [s for s in wf.sheetnames if s.upper().startswith("CDP")]
    hoja = a.hoja_cdp or (sorted(cands, key=lambda s: (len(s), s))[0] if cands else None)
    if not hoja:
        raise SystemExit("No se encontró una hoja CDP; use --hoja-cdp")
    f, v = wf[hoja], wv[hoja]

    def g(ws, ref):
        return ws[ref].value

    out = {
        "codigo": txt(g(v, "B3")), "fecha": txt(g(v, "B4")), "revision": txt(g(v, "B5")),
        "proyecto": txt(g(v, "D3")), "mandante": txt(g(v, "D4")), "direccion": txt(g(v, "D5")),
        "email": txt(g(v, "D6")), "contacto": txt(g(v, "D7")),
        "fuente": f"Extraído de {a.xlsx.split('/')[-1]}, hoja {hoja}",
        "partidas": [], "apu": {}, "materiales": [], "mano_obra": [], "referencias": [],
    }
    sup = txt(g(v, "B6")) or ""
    m = re.search(r"[\d.,]+", sup)
    if m:
        out["superficie_total"] = float(m.group(0).replace(".", "").replace(",", ".")) if "," in m.group(0) else float(m.group(0))

    cap = sub = None
    item_row = {}
    for r in range(11, f.max_row + 1):
        A, B, C = g(v, f"A{r}"), g(v, f"B{r}"), g(v, f"C{r}")
        D, E, Fv = g(v, f"D{r}"), g(v, f"E{r}"), g(v, f"F{r}")
        if B and isinstance(B, str):
            nombre = B.strip()
            up = nombre.upper()
            if up.startswith(("COSTO DIRECTO", "GASTOS GENERALES", "UTILIDADES", "TOTAL", "IVA")):
                if up.startswith("GASTOS GENERALES") and isinstance(E, (int, float)):
                    out["gastos_generales"] = E
                if up.startswith("UTILIDADES") and isinstance(E, (int, float)):
                    out["utilidades"] = E
                continue
            cod = txt(A) or ""
            if re.match(r"^\d+\.0$", cod) or re.match(r"^\d+\.?$", cod):
                cap, sub = f"{cod} {nombre}".strip(), None
            else:
                sub = f"{cod} {nombre}".strip()
            continue
        if A is not None and C:
            it = txt(A)
            p = {"item": it, "capitulo": cap, "descripcion": txt(C), "unidad": txt(D)}
            if sub:
                p["subcapitulo"] = sub
            q = num_o_formula(g(f, f"E{r}"), E)
            if q is not None:
                p["cantidad"] = q
            if isinstance(Fv, str) and not Fv.startswith("="):
                p["por_mandante"] = Fv
            else:
                pf = g(f, f"F{r}")
                if not (isinstance(pf, str) and "APU" in pf.upper()):
                    pu = num_o_formula(pf, Fv)
                    if pu is not None:
                        p["pu"] = pu
                        p["origen_pu"] = "Precio directo en el cuadro original"
            item_row[r] = p
            out["partidas"].append(p)

    # --- hojas APU ---
    tarifas = {}
    for s in wf.sheetnames:
        if not s.upper().startswith("APU"):
            continue
        fs, vs = wf[s], wv[s]
        r = 1
        while r <= fs.max_row:
            if fs.cell(r, 1).value == "Ítem":
                ref = fs.cell(r, 2).value
                mref = RE_REF.search(str(ref)) if isinstance(ref, str) else None
                crow = int(mref.group(3)) if mref else None
                p = item_row.get(crow)
                it = p["item"] if p else txt(vs.cell(r, 2).value)
                bloque = {"materiales": [], "mano_obra": [], "equipos": []}
                sec = None
                rr = r + 1
                while rr <= fs.max_row and fs.cell(rr, 1).value != "Ítem":
                    b = fs.cell(rr, 2).value
                    bu = str(b).upper().strip() if b else ""
                    es_titulo = fs.cell(rr, 1).value in ("N°", "Código") or bu in ("MATERIALES", "MANO DE OBRA") \
                        or bu.startswith(("MAQ. Y EQUIPOS", "MAQ Y EQUIPOS", "MAQUINARIA Y EQUIPOS"))
                    if es_titulo and bu.startswith("MATERIALES"):
                        sec = "materiales"
                    elif es_titulo and bu.startswith("MANO DE OBRA"):
                        sec = "mano_obra"
                    elif es_titulo and bu.startswith("MAQ"):
                        sec = "equipos"
                    elif sec and b and not (isinstance(b, str) and b.startswith("=")):
                        Dq = num_o_formula(fs.cell(rr, 4).value, vs.cell(rr, 4).value)
                        if sec == "materiales":
                            bloque[sec].append({"descripcion": txt(b), "unidad": txt(vs.cell(rr, 3).value), "cantidad": Dq,
                                                "perdida": vs.cell(rr, 6).value or 0,
                                                "precio": num_o_formula(fs.cell(rr, 7).value, vs.cell(rr, 7).value)})
                        elif sec == "mano_obra":
                            bloque[sec].append({"especialidad": txt(b), "cantidad": Dq,
                                                "costo_hd": vs.cell(rr, 6).value, "ls": vs.cell(rr, 7).value})
                        else:
                            bloque[sec].append({"descripcion": txt(b), "unidad": txt(vs.cell(rr, 3).value), "cantidad": Dq,
                                                "costo": num_o_formula(fs.cell(rr, 6).value, vs.cell(rr, 6).value),
                                                "vida_util": vs.cell(rr, 7).value or 1})
                    # tabla lateral de tarifas (J: especialidad, K: líquido, L: costo, M: día)
                    esp = vs.cell(rr, 10).value
                    if isinstance(esp, str) and esp.strip() and isinstance(vs.cell(rr, 12).value, (int, float)):
                        tarifas.setdefault(esp.strip(), {"especialidad": esp.strip(), "liquido_mes": vs.cell(rr, 11).value,
                                                          "costo_mes": vs.cell(rr, 12).value,
                                                          "fuente": f"Tabla de tarifas, columna «{txt(vs.cell(r + 2, 12).value) or txt(fs.cell(8, 12).value) or 'costo'}» ({s})"})
                    rr += 1
                if it and any(bloque.values()):
                    out["apu"][it] = bloque
                r = rr
            else:
                r += 1
    out["mano_obra"] = list(tarifas.values())
    ls = [ln.get("ls") for b in out["apu"].values() for ln in b["mano_obra"] if isinstance(ln.get("ls"), (int, float))]
    if ls:
        out["leyes_sociales"] = max(set(ls), key=ls.count)

    # --- MATERIALES ---
    if "MATERIALES" in wf.sheetnames:
        fm, vm = wf["MATERIALES"], wv["MATERIALES"]
        prov, fecha = txt(vm["B2"].value), txt(vm["E2"].value)
        cat = None
        for r in range(4, fm.max_row + 1):
            if vm.cell(r, 1).value:
                cat = txt(vm.cell(r, 1).value)
            pre, cor, desc = vm.cell(r, 2).value, vm.cell(r, 3).value, vm.cell(r, 4).value
            if pre and desc:
                out["materiales"].append({"categoria": cat, "prefijo": txt(pre), "correlativo": cor, "descripcion": txt(desc),
                                          "unidad": txt(vm.cell(r, 5).value),
                                          "precio": num_o_formula(fm.cell(r, 6).value, vm.cell(r, 6).value),
                                          "rdto": txt(vm.cell(r, 7).value), "proveedor": prov, "fecha": fecha})

    # --- Referencias ---
    if "Referencias" in wf.sheetnames:
        vr = wv["Referencias"]
        nombre = None
        for r in range(1, vr.max_row + 1):
            x, y = vr.cell(r, 1).value, vr.cell(r, 2).value
            if x:
                nombre = txt(x)
            if y:
                out["referencias"].append({"nombre": nombre, "url": txt(y)})

    with open(a.salida, "w", encoding="utf-8") as fo:
        json.dump(out, fo, ensure_ascii=False, indent=1, default=str)
    n_l = sum(len(x) for b in out["apu"].values() for x in b.values())
    print(f"OK: {a.salida} · {len(out['partidas'])} partidas · {len(out['apu'])} APU ({n_l} líneas) · "
          f"{len(out['materiales'])} materiales · {len(out['mano_obra'])} tarifas · {len(out['referencias'])} referencias")


if __name__ == "__main__":
    main()
