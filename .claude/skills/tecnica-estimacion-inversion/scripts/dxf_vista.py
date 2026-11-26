#!/usr/bin/env python3
"""Lee entidades de un DXF con coordenadas (expandiendo bloques) y dibuja zonas como imagen PNG.

Uso como herramienta:
    python3 dxf_vista.py plano.dxf --titulos                 # lista textos-título con su posición
    python3 dxf_vista.py plano.dxf --buscar "F1|ZAPATA"      # textos que calzan con una expresión, con posición
    python3 dxf_vista.py plano.dxf --png zona.png --ventana xmin ymin xmax ymax [--ancho 3000] [--capas 18_FUND,01_FORMA]

Sin librerías externas salvo Pillow. Soporta LINE, LWPOLYLINE, POLYLINE/VERTEX, ARC, CIRCLE, TEXT, MTEXT,
DIMENSION (texto de la medida), INSERT (bloques anidados con escala y rotación) y HATCH (contorno).
Solo espacio modelo (las entidades de espacio papel se omiten).
"""
import argparse
import math
import re
import sys
from collections import defaultdict


def pares(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        it = iter(f)
        for a in it:
            try:
                b = next(it)
            except StopIteration:
                return
            try:
                yield int(a.strip()), b.rstrip("\r\n")
            except ValueError:
                continue


def cargar(path):
    """Devuelve (bloques, entidades). Cada entidad: (tipo, lista de pares (código, valor))."""
    bloques, ents = {}, []
    seccion = None
    actual = None
    bloque = None
    esperando_nombre = False
    for code, val in pares(path):
        v = val.strip()
        if code == 0:
            if actual is not None:
                (bloques[bloque] if seccion == "BLOCKS" and bloque is not None else ents).append(actual)
                actual = None
            if v == "SECTION":
                esperando_nombre = True
                continue
            if v == "ENDSEC":
                seccion = None
                continue
            if seccion == "BLOCKS":
                if v == "BLOCK":
                    bloque = "__pending__"
                    actual = ("BLOCK", [])
                    continue
                if v == "ENDBLK":
                    bloque = None
                    continue
            if seccion in ("ENTITIES", "BLOCKS") and v not in ("EOF",):
                actual = (v, [])
            continue
        if esperando_nombre and code == 2:
            seccion = v
            esperando_nombre = False
            continue
        if actual is not None:
            if actual[0] == "BLOCK":
                if code == 2:
                    bloque = v
                    bloques[bloque] = []
                    actual = None
                continue
            actual[1].append((code, val))
    return bloques, ents


def g(p, code, default=None, cast=float):
    for c, v in p:
        if c == code:
            try:
                return cast(v)
            except ValueError:
                return default
    return default


def gall(p, code, cast=float):
    out = []
    for c, v in p:
        if c == code:
            try:
                out.append(cast(v))
            except ValueError:
                pass
    return out


def limpiar_mtext(t):
    t = re.sub(r"\\[A-Za-z][^;]*;", "", t)
    t = t.replace("\\P", " ").replace("{", "").replace("}", "").replace("%%U", "").replace("%%C", "Ø").replace("%%c", "Ø")
    t = t.replace("%%D", "°").replace("%%P", "±")
    return t.strip()


class T:
    def __init__(self, dx=0, dy=0, sx=1, sy=1, rot=0, parent=None):
        self.dx, self.dy, self.sx, self.sy, self.rot, self.parent = dx, dy, sx, sy, rot, parent

    def __call__(self, x, y):
        x, y = x * self.sx, y * self.sy
        c, s = math.cos(self.rot), math.sin(self.rot)
        x, y = x * c - y * s + self.dx, x * s + y * c + self.dy
        return self.parent(x, y) if self.parent else (x, y)

    def escala(self):
        e = abs(self.sx)
        return e * (self.parent.escala() if self.parent else 1)


def aplanar(bloques, ents, capas=None, prof=0, tr=None, out=None, capa_padre=None):
    """Genera primitivas en coordenadas de mundo: ('L', capa, [(x,y),...]) y ('T', capa, x, y, h, texto)."""
    if out is None:
        out = []
    tr = tr or T()
    for tipo, p in ents:
        if g(p, 67, 0, int) == 1:
            continue
        capa = next((v.strip() for c, v in p if c == 8), "0")
        if capa == "0" and capa_padre:
            capa = capa_padre
        if capas and capa not in capas and tipo != "INSERT":
            continue
        if tipo == "LINE":
            out.append(("L", capa, [tr(g(p, 10, 0), g(p, 20, 0)), tr(g(p, 11, 0), g(p, 21, 0))]))
        elif tipo == "LWPOLYLINE":
            xs, ys = gall(p, 10), gall(p, 20)
            pts = [tr(x, y) for x, y in zip(xs, ys)]
            if g(p, 70, 0, int) & 1 and pts:
                pts.append(pts[0])
            if len(pts) > 1:
                out.append(("L", capa, pts))
        elif tipo in ("ARC", "CIRCLE"):
            cx, cy, r = g(p, 10, 0), g(p, 20, 0), g(p, 40, 0)
            a0, a1 = (g(p, 50, 0), g(p, 51, 360)) if tipo == "ARC" else (0, 360)
            if a1 < a0:
                a1 += 360
            n = max(8, int((a1 - a0) / 6))
            pts = [tr(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
            out.append(("L", capa, pts))
        elif tipo in ("TEXT", "MTEXT", "ATTRIB"):
            txt = "".join(v for c, v in p if c in (3, 1)) if tipo == "MTEXT" else next((v for c, v in p if c == 1), "")
            txt = limpiar_mtext(txt)
            if txt:
                x, y = tr(g(p, 10, 0), g(p, 20, 0))
                out.append(("T", capa, x, y, (g(p, 40, 1) or 1) * tr.escala(), txt))
        elif tipo == "DIMENSION":
            med = g(p, 42)
            txt = next((v for c, v in p if c == 1), "") or ""
            x, y = tr(g(p, 11, 0), g(p, 21, 0))
            if med is not None:
                label = limpiar_mtext(txt.replace("<>", f"{med:.0f}")) if txt else f"{med:.0f}"
                out.append(("T", capa, x, y, 2.5 * tr.escala(), label))
            nombre = next((v.strip() for c, v in p if c == 2), None)
            if nombre and nombre in bloques and prof < 6:
                aplanar(bloques, bloques[nombre], capas, prof + 1, tr, out, capa)
        elif tipo == "INSERT" and prof < 6:
            nombre = next((v.strip() for c, v in p if c == 2), None)
            if nombre not in bloques:
                continue
            sub = T(g(p, 10, 0), g(p, 20, 0), g(p, 41, 1) or 1, g(p, 42, 1) or 1, math.radians(g(p, 50, 0) or 0), tr)
            aplanar(bloques, bloques[nombre], capas, prof + 1, sub, out, capa)
        elif tipo == "HATCH":
            xs, ys = gall(p, 10), gall(p, 20)
            pts = [tr(x, y) for x, y in zip(xs[1:], ys[1:])]
            if len(pts) > 2:
                out.append(("H", capa, pts))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("--titulos", action="store_true")
    ap.add_argument("--buscar")
    ap.add_argument("--png")
    ap.add_argument("--ventana", nargs=4, type=float)
    ap.add_argument("--ancho", type=int, default=3000)
    ap.add_argument("--capas")
    ap.add_argument("--min-texto", type=float, default=7.0, help="alto mínimo en px para dibujar un texto")
    a = ap.parse_args()
    bloques, ents = cargar(a.dxf)
    capas = set(a.capas.split(",")) if a.capas else None
    prim = aplanar(bloques, ents, capas)
    textos = [p for p in prim if p[0] == "T"]
    if a.titulos:
        for _, capa, x, y, h, t in sorted(textos, key=lambda z: -z[4])[:80]:
            if len(t) > 3:
                print(f"{x:12.1f} {y:12.1f}  h={h:7.1f}  [{capa}]  {t[:90]}")
    if a.buscar:
        rx = re.compile(a.buscar, re.I)
        for _, capa, x, y, h, t in textos:
            if rx.search(t):
                print(f"{x:12.1f} {y:12.1f}  h={h:6.1f}  [{capa}]  {t[:120]}")
    if a.png:
        from PIL import Image, ImageDraw, ImageFont
        if a.ventana:
            x0, y0, x1, y1 = a.ventana
        else:
            xs = [pt[0] for p in prim if p[0] in "LH" for pt in p[2]]
            ys = [pt[1] for p in prim if p[0] in "LH" for pt in p[2]]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        k = a.ancho / (x1 - x0)
        W, H = a.ancho, max(1, int((y1 - y0) * k))
        im = Image.new("RGB", (W, H), "white")
        dr = ImageDraw.Draw(im)
        colores = defaultdict(lambda: (40, 40, 40))
        paleta = [(0, 0, 0), (200, 0, 0), (0, 0, 200), (0, 130, 0), (150, 0, 150), (200, 110, 0), (0, 130, 130)]
        for i, c in enumerate(sorted({p[1] for p in prim})):
            colores[c] = paleta[i % len(paleta)]
        def px(pt):
            return ((pt[0] - x0) * k, (y1 - pt[1]) * k)
        for p in prim:
            if p[0] == "H":
                pts = [px(q) for q in p[2]]
                if all(-W < u < 2 * W and -H < v < 2 * H for u, v in pts):
                    dr.polygon(pts, fill=(225, 225, 225))
        for p in prim:
            if p[0] == "L":
                pts = [px(q) for q in p[2]]
                if any(0 <= u <= W and 0 <= v <= H for u, v in pts) or len(pts) == 2:
                    dr.line(pts, fill=colores[p[1]], width=1)
        try:
            fpath = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            cache = {}
            for _, capa, x, y, h, t in textos:
                u, v = px((x, y))
                hp = h * k
                if 0 <= u <= W and 0 <= v <= H and hp >= a.min_texto:
                    s = int(min(hp, 60))
                    if s not in cache:
                        cache[s] = ImageFont.truetype(fpath, s)
                    dr.text((u, v - s), t[:80], fill=(0, 0, 160), font=cache[s])
        except OSError:
            pass
        im.save(a.png)
        print(f"PNG {a.png}: {W}×{H}px · ventana {x0:.0f},{y0:.0f} – {x1:.0f},{y1:.0f} · 1 px = {1/k:.1f} unidades")


if __name__ == "__main__":
    sys.exit(main())
