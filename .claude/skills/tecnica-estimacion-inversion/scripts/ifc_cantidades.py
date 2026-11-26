#!/usr/bin/env python3
"""Cantidades desde un modelo IFC (IFC2X3/IFC4) sin librerías externas.

Uso:
    python3 ifc_cantidades.py modelo.ifc salida.json [--csv elementos.csv]

Por cada muro, viga, losa, pilar, cubierta, escalera, elemento parte, placa y miembro calcula,
desde su geometría de cuerpo (FacetedBrep, también dentro de MappedItem):
  - volumen (m³) por el teorema de la divergencia
  - área horizontal superior (m², caras con normal hacia arriba) → losas, radieres, cubiertas
  - área vertical (m², caras verticales) / 2 → una cara de muros
  - largo aproximado (m, mayor dimensión de la caja envolvente) → vigas y pilares
y lo agrupa por tipo, material y nivel. Si el modelo trae IfcElementQuantity, también las lee.

Las cantidades del modelo de arquitectura sirven para contrastar la cubicación de los planos;
no reemplazan los planos de cálculo (el modelo puede no tener armaduras, uniones ni la estructura final).
"""
import argparse
import csv
import json
import math
import re
from collections import defaultdict

RE_ENT = re.compile(r"^#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*)\);\s*$", re.S)
TIPOS = ("IFCWALL", "IFCWALLSTANDARDCASE", "IFCBEAM", "IFCSLAB", "IFCCOLUMN", "IFCROOF", "IFCSTAIR", "IFCSTAIRFLIGHT",
         "IFCBUILDINGELEMENTPART", "IFCPLATE", "IFCMEMBER", "IFCFOOTING", "IFCRAMP", "IFCRAILING", "IFCCOVERING")


def decode(s):
    s = re.sub(r"\\X\\([0-9A-F]{2})", lambda m: bytes([int(m.group(1), 16)]).decode("latin-1"), s)
    s = re.sub(r"\\X2\\([0-9A-F]+)\\X0\\", lambda m: "".join(chr(int(m.group(1)[i:i + 4], 16)) for i in range(0, len(m.group(1)), 4)), s)
    return s


def parse_args(s):
    """Convierte el texto de argumentos STEP en listas anidadas de str/int-ref/float/None."""
    out, stack, tok, i, n = [], [], "", 0, len(s)
    cur = out
    while i < n:
        c = s[i]
        if c == "'":
            j = i + 1
            buf = ""
            while j < n:
                if s[j] == "'" and j + 1 < n and s[j + 1] == "'":
                    buf += "'"
                    j += 2
                    continue
                if s[j] == "'":
                    break
                buf += s[j]
                j += 1
            cur.append(decode(buf))
            i = j + 1
            tok = ""
            continue
        if c == "(":
            nuevo = []
            if tok.strip():
                nuevo_tipo = tok.strip()
                nuevo.append(nuevo_tipo)
                tok = ""
            cur.append(nuevo)
            stack.append(cur)
            cur = nuevo
        elif c == ")":
            if tok.strip():
                cur.append(conv(tok.strip()))
            tok = ""
            cur = stack.pop()
        elif c == ",":
            if tok.strip():
                cur.append(conv(tok.strip()))
            tok = ""
        else:
            tok += c
        i += 1
    if tok.strip():
        cur.append(conv(tok.strip()))
    return out


def conv(t):
    if t.startswith("#"):
        return int(t[1:])
    if t in ("$", "*"):
        return None
    try:
        return float(t)
    except ValueError:
        return t


def leer(path):
    ents = {}
    buf = ""
    with open(path, "r", encoding="latin-1", errors="replace") as f:
        for line in f:
            buf += line.strip()
            if not buf.endswith(";"):
                continue
            m = RE_ENT.match(buf)
            buf = ""
            if m:
                ents[int(m.group(1))] = (m.group(2), m.group(3))
    return ents


class Modelo:
    def __init__(self, ents):
        self.raw = ents
        self.cache = {}

    def get(self, i):
        if i not in self.cache:
            t, a = self.raw[i]
            self.cache[i] = (t, parse_args(a))
        return self.cache[i]

    def punto(self, i):
        t, a = self.get(i)
        c = a[0]
        return (c[0], c[1], c[2] if len(c) > 2 else 0.0)

    def placement_matrix(self, i):
        """Matriz 3x4 de un IfcAxis2Placement3D o de un operador cartesiano (traslación + rotación + escala)."""
        if i is None:
            return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]
        t, a = self.get(i)
        if t == "IFCAXIS2PLACEMENT3D":
            o = self.punto(a[0])
            z = self.dir(a[1]) if a[1] else (0, 0, 1)
            x = self.dir(a[2]) if a[2] else (1, 0, 0)
            y = norm(cross(z, x))
            x = norm(cross(y, z))
            return [[x[0], y[0], z[0], o[0]], [x[1], y[1], z[1], o[1]], [x[2], y[2], z[2], o[2]]]
        if t.startswith("IFCCARTESIANTRANSFORMATIONOPERATOR3D"):
            x = self.dir(a[0]) if a[0] else (1, 0, 0)
            y = self.dir(a[1]) if a[1] else (0, 1, 0)
            o = self.punto(a[2])
            s = a[3] if isinstance(a[3], float) else 1.0
            z = self.dir(a[4]) if len(a) > 4 and a[4] else norm(cross(x, y))
            return [[x[0] * s, y[0] * s, z[0] * s, o[0]], [x[1] * s, y[1] * s, z[1] * s, o[1]], [x[2] * s, y[2] * s, z[2] * s, o[2]]]
        return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]

    def local_placement(self, i):
        """Matriz global de un IfcLocalPlacement (encadena PlacementRelTo)."""
        if i is None:
            return self.placement_matrix(None)
        t, a = self.get(i)
        if t != "IFCLOCALPLACEMENT":
            return self.placement_matrix(None)
        M = self.placement_matrix(a[1])
        return mul(self.local_placement(a[0]), M) if a[0] else M

    def dir(self, i):
        t, a = self.get(i)
        c = a[0]
        return norm((c[0], c[1], c[2] if len(c) > 2 else 0.0))

    def loops_de_item(self, i, M):
        """Devuelve lista de caras (cada una: lista de loops; cada loop: lista de puntos transformados) y si es cerrado."""
        t, a = self.get(i)
        caras, cerrado = [], False
        if t == "IFCFACETEDBREP":
            shells, cerrado = [a[0]], True
        elif t in ("IFCSHELLBASEDSURFACEMODEL",):
            shells = a[0]
        elif t in ("IFCCLOSEDSHELL", "IFCOPENSHELL"):
            shells, cerrado = [i], t == "IFCCLOSEDSHELL"
        elif t == "IFCMAPPEDITEM":
            rm_t, rm = self.get(a[0])
            M2 = mul(M, mul(self.placement_matrix(a[1]), self.placement_matrix(rm[0])))
            rep_t, rep = self.get(rm[1])
            res, c_all = [], True
            for it in rep[3]:
                cs, c = self.loops_de_item(it, M2)
                res += cs
                c_all = c_all and c
            return res, c_all
        else:
            return [], False
        for sh in shells:
            st, sa = self.get(sh)
            if st == "IFCCLOSEDSHELL":
                cerrado = True
            for fc in sa[0]:
                ft, fa = self.get(fc)
                loops = []
                for b in fa[0]:
                    bt, ba = self.get(b)
                    lt, la = self.get(ba[0])
                    if lt != "IFCPOLYLOOP":
                        continue
                    pts = [apply(M, self.punto(p)) for p in la[0]]
                    if ba[1] in (".F.", "F"):
                        pts = pts[::-1]
                    loops.append(pts)
                if loops:
                    caras.append(loops)
        return caras, cerrado


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(v):
    L = math.sqrt(sum(x * x for x in v)) or 1.0
    return tuple(x / L for x in v)


def mul(A, B):
    R = [[0] * 4 for _ in range(3)]
    for i in range(3):
        for j in range(4):
            R[i][j] = sum(A[i][k] * B[k][j] for k in range(3)) + (A[i][3] if j == 3 else 0)
    return R


def apply(M, p):
    return tuple(M[i][0] * p[0] + M[i][1] * p[1] + M[i][2] * p[2] + M[i][3] for i in range(3))


def medir(caras):
    vol, a_sup, a_vert = 0.0, 0.0, 0.0
    xs, ys, zs = [], [], []
    for loops in caras:
        nx = ny = nz = 0.0
        for pts in loops:
            p0 = pts[0]
            for k in range(1, len(pts) - 1):
                p1, p2 = pts[k], pts[k + 1]
                vol += (p0[0] * (p1[1] * p2[2] - p1[2] * p2[1]) - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0]) + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])) / 6
                c = cross((p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]), (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]))
                nx, ny, nz = nx + c[0] / 2, ny + c[1] / 2, nz + c[2] / 2
            for q in pts:
                xs.append(q[0]); ys.append(q[1]); zs.append(q[2])
        area = math.sqrt(nx * nx + ny * ny + nz * nz)
        if area > 0:
            if nz / area > 0.7:
                a_sup += area
            elif abs(nz / area) < 0.2:
                a_vert += area
    caja = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) if xs else (0, 0, 0)
    medir.minimo = (min(xs), min(ys), min(zs)) if xs else (0, 0, 0)
    return abs(vol), a_sup, a_vert, caja


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ifc")
    ap.add_argument("salida")
    ap.add_argument("--csv")
    a = ap.parse_args()
    raw = leer(a.ifc)
    m = Modelo(raw)
    unidad = 0.001 if any("IFCSIUNIT" == t and ".MILLI." in s and ".LENGTHUNIT." in s for t, s in raw.values()) else 1.0

    material, nivel = {}, {}
    for i, (t, s) in raw.items():
        if t == "IFCRELASSOCIATESMATERIAL":
            _, ar = m.get(i)
            mt, ma = m.get(ar[5])
            nombre = ma[0] if mt == "IFCMATERIAL" else mt
            for e in ar[4]:
                material[e] = nombre
        elif t == "IFCRELCONTAINEDINSPATIALSTRUCTURE":
            _, ar = m.get(i)
            st, sa = m.get(ar[5])
            for e in ar[4]:
                nivel[e] = sa[2]
    # elementos agregados (partes) heredan nivel del padre
    for i, (t, s) in raw.items():
        if t == "IFCRELAGGREGATES":
            _, ar = m.get(i)
            for e in ar[5]:
                if ar[4] in nivel and e not in nivel:
                    nivel[e] = nivel[ar[4]]

    elementos = []
    for i, (t, s) in raw.items():
        if t not in TIPOS:
            continue
        _, ar = m.get(i)
        rep = ar[6] if len(ar) > 6 else None
        M0 = m.local_placement(ar[5]) if len(ar) > 5 else m.placement_matrix(None)
        caras, cerrado = [], True
        if rep:
            _, pds = m.get(rep)
            for r in pds[2]:
                rt, ra = m.get(r)
                if ra[1] not in ("Body", "Facetation", None):
                    continue
                for it in ra[3]:
                    cs, c = m.loops_de_item(it, M0)
                    caras += cs
                    cerrado = cerrado and c
        vol, a_sup, a_vert, caja = medir(caras) if caras else (0, 0, 0, (0, 0, 0))
        u3, u2 = unidad ** 3, unidad ** 2
        elementos.append({
            "id": i, "tipo": t.replace("IFC", ""), "nombre": ar[2], "tipo_objeto": ar[4] if len(ar) > 4 else None,
            "material": material.get(i), "nivel": nivel.get(i), "solido_cerrado": cerrado and bool(caras),
            "volumen_m3": round(vol * u3, 4) if cerrado else None, "area_sup_m2": round(a_sup * u2, 3),
            "area_vertical_1cara_m2": round(a_vert * u2 / 2, 3), "largo_max_m": round(max(caja) * unidad, 3),
            "caja_m": [round(c * unidad, 3) for c in caja],
            "min_m": [round(c * unidad, 3) for c in getattr(medir, "minimo", (0, 0, 0))] if caras else None,
        })

    resumen = defaultdict(lambda: {"n": 0, "volumen_m3": 0.0, "area_sup_m2": 0.0, "area_vertical_1cara_m2": 0.0, "largo_m": 0.0, "sin_solido": 0})
    for e in elementos:
        k = f"{e['tipo']} | {e['material']} | {e['nivel']}"
        r = resumen[k]
        r["n"] += 1
        r["volumen_m3"] += e["volumen_m3"] or 0
        r["area_sup_m2"] += e["area_sup_m2"]
        r["area_vertical_1cara_m2"] += e["area_vertical_1cara_m2"]
        r["largo_m"] += e["largo_max_m"]
        r["sin_solido"] += 0 if e["solido_cerrado"] else 1
    res = {k: {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in sorted(resumen.items())}
    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump({"archivo": a.ifc, "resumen": res, "elementos": elementos}, f, ensure_ascii=False, indent=1)
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[k for k in elementos[0] if k not in ("caja_m", "min_m")], extrasaction="ignore")
            w.writeheader()
            w.writerows(elementos)
    print(f"{len(elementos)} elementos. Resumen por tipo | material | nivel:")
    for k, v in res.items():
        print(f"  {k:70s} n={v['n']:4d}  V={v['volumen_m3']:9.2f} m³  Asup={v['area_sup_m2']:9.2f} m²  "
              f"Avert={v['area_vertical_1cara_m2']:9.2f} m²  L={v['largo_m']:8.1f} m  sin sólido={v['sin_solido']}")


if __name__ == "__main__":
    main()
