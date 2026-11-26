#!/usr/bin/env python3
"""Extrae de un plano o especificación en PDF lo necesario para cubicar.

Uso:
    python3 leer_pdf_plano.py documento.pdf carpeta_salida [--paginas 1-3] [--dpi 150]

Genera en carpeta_salida:
  - pagina-N.png        imagen de cada página, para revisarla visualmente (cotas, cortes, detalles)
  - texto.txt           todo el texto, página por página (ET, notas generales, cuadros, rótulos)
  - tablas.json         tablas detectadas (cuadros de armaduras, de vanos, de terminaciones, listas de materiales)
  - resumen.json        escala declarada, cotas numéricas encontradas, ejes y códigos de elementos por página

Si el PDF es escaneado (sin texto), solo quedan las imágenes: leerlas visualmente y declarar
las medidas obtenidas como "leídas de imagen", con su incertidumbre.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import pdfplumber

RE_ESCALA = re.compile(r"ESC(?:ALA)?\.?\s*:?\s*1\s*[:/]\s*(\d{1,4})", re.I)
RE_COTA = re.compile(r"(?<![\w.])(\d{1,3}(?:[.,]\d{1,3})?)(?![\w.])")
RE_ELEM = re.compile(r"\b(Z|P|V|C|L|M|F|PL|VA|VI|ZC)\s?-?\d{1,3}[A-Z]?\b")
RE_EJE = re.compile(r"\bEJE\s+([A-Z0-9]{1,3})\b", re.I)


def rango(s, n):
    if not s:
        return list(range(1, n + 1))
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("salida")
    ap.add_argument("--paginas")
    ap.add_argument("--dpi", type=int, default=150)
    a = ap.parse_args()
    out = Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)

    textos, tablas, resumen = [], [], []
    with pdfplumber.open(a.pdf) as pdf:
        pags = rango(a.paginas, len(pdf.pages))
        for n in pags:
            pg = pdf.pages[n - 1]
            t = pg.extract_text() or ""
            textos.append(f"===== Página {n} =====\n{t}")
            for i, tb in enumerate(pg.extract_tables() or []):
                tablas.append({"pagina": n, "tabla": i + 1, "filas": tb})
            palabras = pg.extract_words() or []
            resumen.append({
                "pagina": n,
                "tamano_pt": [round(pg.width), round(pg.height)],
                "tiene_texto": bool(t.strip()),
                "escala": sorted(set("1:" + m for m in RE_ESCALA.findall(t))),
                "ejes": sorted(set(RE_EJE.findall(t))),
                "elementos": sorted(set(m.group(0).replace(" ", "") for m in RE_ELEM.finditer(t)))[:200],
                "cotas_numericas": [w["text"] for w in palabras if RE_COTA.fullmatch(w["text"])][:300],
                "lineas_vectoriales": len(pg.lines) + len(pg.rects) + len(pg.curves),
            })
    (out / "texto.txt").write_text("\n\n".join(textos), encoding="utf-8")
    (out / "tablas.json").write_text(json.dumps(tablas, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run(["pdftoppm", "-png", "-r", str(a.dpi), "-f", str(pags[0]), "-l", str(pags[-1]), a.pdf,
                    str(out / "pagina")], check=False)
    print(f"Listo: {len(pags)} páginas → {out}/ (texto.txt, tablas.json, resumen.json, pagina-*.png)")
    for r in resumen:
        print(f"  pág. {r['pagina']}: escala {r['escala'] or 'no declarada'} · {len(r['elementos'])} códigos de elemento · "
              f"{len(r['cotas_numericas'])} números · {'con texto' if r['tiene_texto'] else 'SIN TEXTO (escaneado)'}")


if __name__ == "__main__":
    main()
