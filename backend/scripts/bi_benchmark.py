"""Mide cuanto tarda el modulo BI de punta a punta (modelo + validacion + SQL).

Corre DENTRO del backend (o con la misma JWT_SECRET) y habla con la API real:

    python scripts/bi_benchmark.py --url http://localhost:5001 \
        --salida /app/docs/BI_TIEMPOS_CONSULTAS.md

Para medir en la nube, ejecutalo desde un pod del mismo namespace apuntando al
Service del backend (y otra vez desde fuera, por el Ingress, para sumar la red):
la diferencia entre ambas corridas es la latencia de infraestructura.

Cada pregunta se hace dos veces: la primera paga al modelo; la segunda sale de
la cache de preguntas y mide solo validacion + SQL.
"""

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request

import jwt

PREGUNTAS = [
    ("kpi", "¿Cuántos productos hay registrados?"),
    ("agrupacion", "Cuántas incidencias hay por tipo"),
    ("top_n", "Top 8 productos por existencias"),
    ("join", "Total de facturas por cliente"),
    ("dashboard", "Dashboard general de operaciones"),
]


def token(secret: str, **datos) -> str:
    return jwt.encode({"id_user": 1, **datos}, secret, algorithm="HS256")


def preguntar(url: str, tk: str, pregunta: str, timeout: int):
    cuerpo = json.dumps({"prompt": pregunta}).encode()
    req = urllib.request.Request(f"{url}/api/v1/bi/query", data=cuerpo, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {tk}"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            datos, http = json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        datos, http = json.loads(e.read() or b"{}"), e.code
    return (time.monotonic() - t0) * 1000, http, datos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:5001")
    ap.add_argument("--secret", default=None, help="JWT_SECRET (por omision, el del entorno)")
    ap.add_argument("--rol", type=int, default=2, help="id_permission del rol NO admin a comparar")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--salida", default="")
    args = ap.parse_args()

    import os
    secret = args.secret or os.environ.get("JWT_SECRET", "dev-secret-change-me")
    perfiles = [("admin", token(secret, is_superuser=True)),
                (f"rol {args.rol}", token(secret, id_permission=args.rol))]

    filas, md = [], []
    for perfil, tk in perfiles:
        for clave, q in PREGUNTAS:
            for intento in ("modelo", "cache"):
                try:
                    ms, http, d = preguntar(args.url, tk, q, args.timeout)
                except Exception as e:           # timeout, red
                    ms, http, d = args.timeout * 1000, 0, {"error": {"tipo": str(e)[:60]}}
                meta = d.get("meta") or {}
                sql_ms = sum(w.get("ms", 0) for w in d.get("widgets", []))
                fila = dict(perfil=perfil, tipo=clave, intento=intento, http=http,
                            ok=bool(d.get("ok")), total_ms=round(ms),
                            modelo_ms=meta.get("ms_modelo"), sql_ms=sql_ms,
                            tokens_in=meta.get("tokens_prompt"), tokens_out=meta.get("tokens_respuesta"),
                            error=(d.get("error") or {}).get("tipo"))
                filas.append(fila)
                print(json.dumps(fila, ensure_ascii=False), flush=True)

    def p(vals, q):
        vals = sorted(v for v in vals if v is not None)
        if not vals:
            return "—"
        return f"{vals[min(len(vals) - 1, int(round(q * (len(vals) - 1))))] / 1000:.1f} s"

    md.append("# Tiempos de consulta del módulo BI\n")
    md.append(f"Generado con `scripts/bi_benchmark.py` contra `{args.url}` "
              f"el {time.strftime('%Y-%m-%d %H:%M')}.\n")
    for intento, titulo in (("modelo", "Con modelo (consulta nueva)"), ("cache", "Desde caché de preguntas")):
        sel = [f for f in filas if f["intento"] == intento]
        ok = [f for f in sel if f["ok"]]
        md.append(f"\n## {titulo}\n")
        md.append(f"- Consultas: {len(sel)}; correctas: {len(ok)}")
        md.append(f"- Total p50 / p95: {p([f['total_ms'] for f in ok], .5)} / {p([f['total_ms'] for f in ok], .95)}")
        if intento == "modelo":
            md.append(f"- Solo modelo (Ollama) p50: {p([f['modelo_ms'] for f in ok], .5)}")
        md.append(f"- Solo SQL p50: {p([f['sql_ms'] for f in ok], .5)}")
    md.append("\n## Detalle\n")
    md.append("| Perfil | Pregunta | Intento | HTTP | OK | Total | Modelo | SQL | Tokens in/out | Error |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for f in filas:
        md.append(f"| {f['perfil']} | {f['tipo']} | {f['intento']} | {f['http']} | {'sí' if f['ok'] else 'no'} | "
                  f"{f['total_ms'] / 1000:.1f} s | {(f['modelo_ms'] or 0) / 1000:.1f} s | {f['sql_ms']} ms | "
                  f"{f['tokens_in'] or '—'}/{f['tokens_out'] or '—'} | {f['error'] or ''} |")
    texto = "\n".join(md) + "\n"
    if args.salida:
        with open(args.salida, "w", encoding="utf-8") as fh:
            fh.write(texto)
    print(texto)


if __name__ == "__main__":
    main()
