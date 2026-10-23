"""Mide la PRECISION del asistente BI contra consultas de oro.

Para cada pregunta de database/datasets/bi_preguntas_oro.json se compara el
RESULTADO que devuelve el asistente con el de la consulta de oro (no el texto del
SQL: dos SQL distintos pueden ser igual de correctos). Reporta aciertos por
conjunto, por via (respuesta preparada o modelo) y los fallos con su SQL.

    python scripts/bi_evaluar_oro.py --conjunto prueba
    python scripts/bi_evaluar_oro.py --solo o01,o02 --jsonl fallos.jsonl

Se pregunta como administrador con ?debug_sql=1 para poder ver el SQL generado.
`--jsonl` guarda cada fallo como ejemplo (pregunta -> SQL de oro) listo para
agregarse al banco con `--aprender`: asi los errores del modelo se convierten en
ejemplos verificados.
"""

import argparse
import decimal
import json
import os
import time
import urllib.error
import urllib.request

import jwt
from sqlalchemy import create_engine, text


def celdas(filas):
    salida = []
    for f in filas:
        fila = []
        for v in f:
            if isinstance(v, (decimal.Decimal, float)):
                v = round(float(v), 2)
            elif v is not None and not isinstance(v, (int, str, bool)):
                v = str(v)[:10]
            fila.append(v)
        salida.append(tuple(fila))
    return salida


def comparar(esperado, obtenido, ordenado):
    """Mismo contenido (orden indiferente salvo `ordenado`); las columnas se comparan por valor."""
    e, o = celdas(esperado), celdas(obtenido)
    if len(e) != len(o):
        return False
    if not ordenado:
        e, o = sorted(map(str, e)), sorted(map(str, o))
    return e == o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:5001")
    ap.add_argument("--dataset", default="/database/datasets/bi_preguntas_oro.json")
    ap.add_argument("--conjunto", default="", help="entrenamiento | prueba (vacio = todas)")
    ap.add_argument("--solo", default="")
    ap.add_argument("--jsonl", default="", help="guarda los fallos como ejemplos de oro")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    from app.bi.config import AjustesBI
    engine = create_engine(AjustesBI.desde_entorno().database_url)
    tk = jwt.encode({"id_user": 1, "is_superuser": True, "exp": int(time.time()) + 14400},
                    os.environ.get("JWT_SECRET", "dev-secret-change-me"), algorithm="HS256")
    preguntas = json.load(open(args.dataset, encoding="utf-8"))["preguntas"]
    solo = {x for x in args.solo.split(",") if x}

    ok = total = 0
    por_via = {}
    fallos = []
    for p in preguntas:
        if args.conjunto and p["conjunto"] != args.conjunto:
            continue
        if solo and p["id"] not in solo:
            continue
        total += 1
        with engine.connect() as c:
            esperado = c.execute(text(p["oro"])).fetchall()
        t0 = time.time()
        req = urllib.request.Request(
            f"{args.url}/api/v1/bi/query?debug_sql=1", method="POST",
            data=json.dumps({"prompt": p["pregunta"]}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {tk}"})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=args.timeout).read())
        except urllib.error.HTTPError as e:
            d = json.loads(e.read() or b"{}")
        except Exception as e:
            d = {"error": {"tipo": str(e)[:60]}}
        w = (d.get("widgets") or [{}])[0]
        via = (d.get("meta") or {}).get("modelo", "?")
        via = "receta" if via == "receta" else "modelo"
        filas = [tuple(r.get(c) for c in w.get("columnas", [])) for r in w.get("filas", [])]
        bien = bool(d.get("ok")) and comparar(esperado, filas, p.get("ordenado", False))
        ok += bien
        por_via.setdefault(via, [0, 0])
        por_via[via][0] += bien
        por_via[via][1] += 1
        print(("OK   " if bien else "FALLA"), f"{time.time() - t0:5.0f}s [{via:6s}] {p['id']} {p['pregunta']}", flush=True)
        if not bien:
            print("       generado:", (w.get("sql") or str((d.get("error") or {}).get("tipo")))[:200].replace("\n", " "))
            print("       esperado:", p["oro"][:200])
            fallos.append(p)
    print(f"\n{ok}/{total} correctas ({100 * ok // max(total, 1)} %)  por via: "
          + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in por_via.items()))
    if args.jsonl and fallos:
        with open(args.jsonl, "w", encoding="utf-8") as fh:
            for p in fallos:
                fh.write(json.dumps({"id": p["id"], "pregunta": p["pregunta"], "sql": p["oro"]}, ensure_ascii=False) + "\n")
        print(f"{len(fallos)} fallos guardados en {args.jsonl}")


if __name__ == "__main__":
    main()
