"""Compara la salida de `conciliar_piezas_por_estado.sql` contra el CSV de estado de piezas de Alan.

Uso:  python3 backend/scripts/conciliar_piezas_por_estado.py piezas.csv \
          docs/despliegues/2026-09-30_estado_de_piezas_adser.csv

Solo lee. El CSV trae el estado ANTIGUO en texto (`estado_guardado`) y los renglones abiertos de
produccion al 30-sep: el "esperado" de cada pieza sale de ahi con la misma prioridad del KPI. Sirve para
comprobar que la derivacion cuadra con el legado; las diferencias se listan para revisarlas una por una.
"""
import csv, sys, collections
C = collections.Counter
alan = {int(r["id_producto"]): r for r in csv.DictReader(open(sys.argv[2], encoding="utf-8-sig"))}
der = {}
for linea in open(sys.argv[1], encoding="utf-8"):
    linea = linea.strip()
    if linea and linea[0].isdigit():
        i, c = linea.split(",", 1); der[int(i)] = c
print("piezas derivadas:", len(der), "| en CSV de Alan:", len(alan))
print("por categoria:", dict(C(der.values())))
print("solo en BD:", len(set(der) - set(alan)), "| solo en CSV:", len(set(alan) - set(der)))
esperado_baja = {"DESTRUCCION": "Destruccion", "EXTRAVIADO": "Extraviado", "DAÑADO": "Dañado", "EQ. DAÑADOS": "Dañado"}
dif = []
for i, r in alan.items():
    if i not in der: continue
    g = r["estado_guardado"]
    if g in esperado_baja: esp = esperado_baja[g]
    else: esp = "Salida" if int(r["renglones_abiertos_en_prod_hoy"] or 0) > 0 else "Entrada"
    if esp != der[i]: dif.append((i, r["codigo"], g, esp, der[i]))
print("piezas que difieren del CSV:", len(dif))
for d in dif[:40]: print("  ", d)
