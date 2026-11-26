#!/usr/bin/env python3
"""Resume un plano DXF (ASCII) para cubicar, sin librerías externas.

Uso:
    python3 leer_dxf.py plano.dxf [--unidad mm|cm|m] [--capa TEXTO] [--json salida.json]

Entrega, por capa:
  - largo total de líneas, polilíneas y arcos (para cerchas, vigas, muros, cañerías, cierres)
  - área y perímetro de cada polilínea cerrada (para losas, radieres, recintos, cubiertas)
  - cantidad de cada bloque insertado (para pilares, zapatas, puertas, ventanas, artefactos)
  - textos y cotas (para leer rótulos, ejes y medidas acotadas)

Los DWG deben exportarse antes a DXF (AutoCAD: Guardar como → DXF; o el conversor gratuito de ODA).
Las medidas se convierten a metros según --unidad (por defecto, la que declara el archivo en $INSUNITS;
si no la declara, se asume mm y se avisa).
"""
import argparse
import json
import math
import sys
from collections import defaultdict

INSUNITS = {1: ("in", 0.0254), 2: ("ft", 0.3048), 4: ("mm", 0.001), 5: ("cm", 0.01), 6: ("m", 1.0)}
FACT = {"mm": 0.001, "cm": 0.01, "m": 1.0}


def pares(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for i in range(0, len(lines) - 1, 2):
        try:
            yield int(lines[i].strip()), lines[i + 1].strip()
        except ValueError:
            continue


def entidades(path):
    """Devuelve (header, entidades) con entidades como dict de listas por código de grupo."""
    header, ents = {}, []
    seccion, actual, var = None, None, None
    for code, val in pares(path):
        if code == 0:
            if actual is not None:
                ents.append(actual)
                actual = None
            if val == "SECTION":
                seccion = "?"
                continue
            if val == "ENDSEC":
                seccion = None
                continue
            if seccion == "ENTITIES" or seccion == "BLOCKS_SKIP":
                actual = {"tipo": val, "g": defaultdict(list)}
            continue
        if seccion == "?" and code == 2:
            seccion = val if val in ("HEADER", "ENTITIES") else "OTRA"
            continue
        if seccion == "HEADER":
            if code == 9:
                var = val
            elif var:
                header.setdefault(var, val)
        elif actual is not None:
            actual["g"][code].append(val)
    if actual is not None:
        ents.append(actual)
    return header, ents


def fl(g, code, i=0, default=0.0):
    try:
        return float(g[code][i])
    except (IndexError, ValueError):
        return default


def poli_area_perim(pts, cerrada):
    per = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    area = 0.0
    if cerrada and len(pts) >= 3:
        per += math.dist(pts[-1], pts[0])
        area = abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                       for i in range(len(pts)))) / 2
    return area, per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("--unidad", choices=list(FACT))
    ap.add_argument("--capa", help="solo capas que contengan este texto")
    ap.add_argument("--json")
    a = ap.parse_args()

    header, ents = entidades(a.dxf)
    aviso = None
    if a.unidad:
        k, uname = FACT[a.unidad], a.unidad
    else:
        code = int(float(header.get("$INSUNITS", 0) or 0))
        uname, k = INSUNITS.get(code, ("mm", 0.001))
        if code not in INSUNITS:
            aviso = "El archivo no declara unidades ($INSUNITS); se asumió mm. Confirmar con una cota conocida."

    capas = defaultdict(lambda: {"largo_m": 0.0, "areas_m2": [], "bloques": defaultdict(int), "textos": [], "cotas_m": []})
    for e in ents:
        g, t = e["g"], e["tipo"]
        capa = (g[8][0] if g[8] else "0")
        if a.capa and a.capa.lower() not in capa.lower():
            continue
        c = capas[capa]
        if t == "LINE":
            c["largo_m"] += math.dist((fl(g, 10), fl(g, 20)), (fl(g, 11), fl(g, 21))) * k
        elif t == "LWPOLYLINE":
            pts = list(zip([float(x) for x in g[10]], [float(y) for y in g[20]]))
            cerrada = bool(int(fl(g, 70)) & 1)
            area, per = poli_area_perim(pts, cerrada)
            c["largo_m"] += per * k
            if cerrada:
                c["areas_m2"].append(round(area * k * k, 3))
        elif t == "ARC":
            ang = (fl(g, 51) - fl(g, 50)) % 360
            c["largo_m"] += math.radians(ang) * fl(g, 40) * k
        elif t == "CIRCLE":
            c["largo_m"] += 2 * math.pi * fl(g, 40) * k
        elif t == "INSERT":
            c["bloques"][g[2][0] if g[2] else "?"] += 1
        elif t in ("TEXT", "MTEXT"):
            txt = " ".join(g[3] + g[1]).replace("\\P", " ").strip()
            if txt:
                c["textos"].append(txt)
        elif t == "DIMENSION":
            med = fl(g, 42, default=None)
            if med is not None:
                c["cotas_m"].append(round(med * k, 3))

    out = {"archivo": a.dxf, "unidad_dibujo": uname, "aviso": aviso, "capas": {}}
    for capa, c in sorted(capas.items()):
        out["capas"][capa] = {
            "largo_total_m": round(c["largo_m"], 2),
            "polilineas_cerradas": len(c["areas_m2"]),
            "area_total_m2": round(sum(c["areas_m2"]), 2),
            "areas_m2": c["areas_m2"][:200],
            "bloques": dict(c["bloques"]),
            "textos": c["textos"][:200],
            "cotas_m": c["cotas_m"][:200],
        }
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Archivo: {a.dxf} · unidad de dibujo: {uname}")
    if aviso:
        print("AVISO:", aviso)
    for capa, c in out["capas"].items():
        print(f"\n[{capa}] largo {c['largo_total_m']} m · {c['polilineas_cerradas']} áreas cerradas = {c['area_total_m2']} m²")
        if c["bloques"]:
            print("  bloques:", c["bloques"])
        if c["cotas_m"]:
            print("  cotas (m):", c["cotas_m"][:20], "..." if len(c["cotas_m"]) > 20 else "")
        if c["textos"]:
            print("  textos:", c["textos"][:15], "..." if len(c["textos"]) > 15 else "")


if __name__ == "__main__":
    sys.exit(main())
