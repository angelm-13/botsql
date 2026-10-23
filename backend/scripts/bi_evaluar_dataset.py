"""Corre las preguntas de database/datasets/bi_preguntas_prueba.json contra la
API del modulo BI y reporta cuantas pasan.

    python scripts/bi_evaluar_dataset.py --url http://localhost:5001 \
        --dataset /database/datasets/bi_preguntas_prueba.json [--solo inv-02,fac-01]

Se pregunta como administrador con `?debug_sql=1` (unico caso en que la API
devuelve el SQL) para poder comprobar que tablas toco. Criterios por pregunta:
  * tablas      : el SQL nombra al menos una de las tablas esperadas
  * filas_exactas: algun widget devolvio exactamente ese numero de filas
  * debe_rechazar: la respuesta NO es ok (o el SQL fue rechazado)
  * dashboard   : la respuesta trae mas de un widget
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request

import jwt


def consultar(url, tk, pregunta, timeout):
    req = urllib.request.Request(
        f"{url}/api/v1/bi/query?debug_sql=1", method="POST",
        data=json.dumps({"prompt": pregunta}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tk}"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return time.monotonic() - t0, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return time.monotonic() - t0, json.loads(e.read() or b"{}")


def evaluar(p, d):
    fallos = []
    widgets = d.get("widgets") or []
    sql = " ".join((w.get("sql") or "") for w in widgets).lower()
    if p.get("debe_rechazar"):
        if d.get("ok") and any(w.get("ok") for w in widgets):
            fallos.append("debia rechazarse y se ejecuto")
        return fallos
    if not d.get("ok"):
        return [f"no ok: {(d.get('error') or {}).get('tipo')}"]
    if p.get("tablas") and not any(t in sql for t in p["tablas"]):
        fallos.append(f"el SQL no toca ninguna de {p['tablas']}")
    if p.get("filas_exactas") is not None and not any(w.get("total_filas") == p["filas_exactas"] for w in widgets):
        fallos.append(f"filas esperadas {p['filas_exactas']}, hubo {[w.get('total_filas') for w in widgets]}")
    if p.get("grafica") and not any((w.get("visualization") or {}).get("chart_type") == p["grafica"] for w in widgets):
        fallos.append(f"grafica esperada {p['grafica']}")
    if p.get("dashboard") and len(widgets) < 2:
        fallos.append("se esperaba un dashboard (>1 widget)")
    return fallos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:5001")
    ap.add_argument("--dataset", default="/database/datasets/bi_preguntas_prueba.json")
    ap.add_argument("--solo", default="")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    secret = os.environ.get("JWT_SECRET", "dev-secret-change-me")
    tk = jwt.encode({"id_user": 1, "is_superuser": True}, secret, algorithm="HS256")
    with open(args.dataset, encoding="utf-8") as fh:
        preguntas = json.load(fh)["preguntas"]
    solo = {x for x in args.solo.split(",") if x}

    ok = total = 0
    for p in preguntas:
        if solo and p["id"] not in solo:
            continue
        total += 1
        try:
            seg, d = consultar(args.url, tk, p["pregunta"], args.timeout)
            fallos = evaluar(p, d)
        except Exception as e:
            seg, fallos = 0, [f"excepcion: {str(e)[:80]}"]
        ok += not fallos
        print(f"{'PASA ' if not fallos else 'FALLA'} {p['id']:8s} {seg:6.1f}s  {p['pregunta']}"
              + ("" if not fallos else f"\n        -> {'; '.join(fallos)}"), flush=True)
    print(f"\n{ok}/{total} preguntas pasan")


if __name__ == "__main__":
    main()
