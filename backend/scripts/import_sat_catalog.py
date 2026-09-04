#!/usr/bin/env python
"""Importa el catalogo c_ClaveProdServ del SAT a la tabla `sat_product_key`.

Uso:
    python scripts/import_sat_catalog.py [ruta_al_csv]

Sin argumento toma `backend/data/c_ClaveProdServ.csv`. Es idempotente: se puede
volver a correr cuando el SAT publique una version nueva del catalogo.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CSV = ROOT / "data" / "c_ClaveProdServ.csv"


def main() -> int:
    from app.services.sat_catalog_service import catalog_status, import_product_keys

    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.is_file():
        print(f"No se encontro el catalogo en {csv_path}")
        print("Descargalo del portal del SAT (c_ClaveProdServ) y vuelve a intentar.")
        return 1

    print(f"Importando {csv_path} ...")
    result = import_product_keys(csv_path)
    total = catalog_status()["total"]
    print(
        f"Listo: {result['created']} nuevas, {result['updated']} actualizadas, "
        f"{result.get('unchanged', 0)} sin cambios, {result['skipped']} filas "
        f"ignoradas. Total en catalogo: {total}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
