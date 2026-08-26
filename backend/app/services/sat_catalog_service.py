"""Busqueda e importacion del catalogo c_ClaveProdServ del SAT.

La busqueda es el nucleo de la captura: sin ella hay que teclear de memoria una
clave de 8 digitos. Funciona sobre el catalogo real cargado en la base, nunca
inventa claves, y es agnostica al giro de la empresa.

Tres cosas la hacen util en espanol:

* se normaliza el texto (minusculas, sin acentos) en la tabla y en la consulta;
* se descartan las palabras vacias, que si no arrastran miles de filas de ruido;
* se expanden sinonimos y frases, porque el catalogo usa terminos formales que
  rara vez coinciden con como escribe la gente ("reparacion pc" contra
  "Mantenimiento y soporte de hardware de computador").
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

from sqlalchemy import case, func, or_, select

from app.models.sat_product_key import SatProductKey, normalize_search_text
from app.models.session import transaction_context


DEFAULT_LIMIT = 15
MAX_LIMIT = 50

# Palabras vacias del espanol. Sin descartarlas, "curso de computacion" hace
# match con cualquier fila que contenga "de" y el resultado es puro ruido.
STOPWORDS = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "u",
    "con", "para", "por", "del", "al", "en", "a", "su", "sus", "lo", "le", "que",
}

# Sinonimos y abreviaturas, ya normalizados. El catalogo del SAT dice
# "computador" y no "pc" ni "laptop"; dice "mantenimiento" y no "reparacion".
SYNONYMS = {
    "pc": ["computador", "computadora", "computadores", "computo"],
    "pcs": ["computador", "computadora", "computadores"],
    "compu": ["computador", "computadora", "computadores"],
    "computadora": ["computador", "computadores", "computo"],
    "computadoras": ["computador", "computadores"],
    "laptop": ["computador portatil", "portatil", "computador"],
    "notebook": ["computador portatil", "portatil"],
    "ordenador": ["computador", "computadora"],
    "computo": ["computador", "computadora", "computadores"],
    "computacion": ["computador", "computadora", "computadores"],
    "informatica": ["computador", "computadora", "sistemas"],
    # "soporte" no entra como sinonimo de reparacion: arrastra las bases fisicas
    # para computador, que no son un servicio.
    "reparacion": ["mantenimiento", "reparaciones"],
    "reparaciones": ["mantenimiento", "reparacion"],
    "reparar": ["reparacion", "mantenimiento"],
    "mantenimiento": ["reparacion"],
    "cel": ["celular", "telefono"],
    "celular": ["telefono", "movil"],
    "tel": ["telefono"],
    "soft": ["software", "programa"],
    "software": ["programa", "sistema", "aplicacion"],
    "programa": ["software", "sistema"],
    "impresora": ["impresion", "impresoras"],
    "flete": ["transporte", "carga"],
    "fletes": ["transporte", "carga"],
    "obra": ["construccion"],
    "albanileria": ["construccion"],
    "abogado": ["juridico", "legal"],
    "contador": ["contabilidad", "contable"],
    "renta": ["arrendamiento", "alquiler"],
    "alimento": ["comida", "alimenticio"],
    "alimentos": ["comida", "alimenticio"],
}

# Frases que conviene traducir enteras antes de partir en palabras: en Mexico
# "equipo de computo" es una computadora, pero tokenizado "equipo" arrastra
# equipo medico y de vehiculo, y las claves de computo ni dicen "equipo".
PHRASES = {
    "equipo de computo": "computador",
    "equipos de computo": "computador",
    "equipo de computacion": "computador",
    "equipo de oficina": "oficina",
    "material de construccion": "construccion",
    "servicio de limpieza": "limpieza",
}


def _variants(token: str) -> list[str]:
    return [token, *SYNONYMS.get(token, [])]


def _tokenize(query: str) -> list[str]:
    text = normalize_search_text(query)
    for phrase, replacement in PHRASES.items():
        text = text.replace(phrase, replacement)
    tokens = [token for token in text.split() if len(token) >= 2]
    meaningful = [token for token in tokens if token not in STOPWORDS]
    # Si al quitar las vacias no queda nada, se conservan las originales.
    return meaningful or tokens


def _matches(token: str):
    conditions = []
    for variant in _variants(token):
        pattern = f"%{variant}%"
        conditions.append(SatProductKey.description_norm.like(pattern))
        conditions.append(SatProductKey.keywords_norm.like(pattern))
    return or_(*conditions)


def _relevance(row, tokens: list[str]) -> int:
    """Puntua la calidad del match. Mide solo eso, no conoce giros."""
    description = row.description_norm or ""
    keywords = row.keywords_norm or ""
    score = 0
    for token in tokens:
        variants = _variants(token)
        in_description = any(variant in description for variant in variants)
        in_keywords = any(variant in keywords for variant in variants)
        if not (in_description or in_keywords):
            continue
        score += 3  # la palabra, o un sinonimo, esta cubierta
        if any(re.search(rf"\b{re.escape(variant)}\b", description) for variant in variants):
            score += 3  # palabra completa en la descripcion: senal fuerte
        elif in_description:
            score += 1
    return score


def search_product_keys(query, limit=DEFAULT_LIMIT) -> list[dict]:
    """Hasta `limit` claves que coinciden con `query`.

    Con digitos busca por prefijo de clave; con texto exige cobertura de
    palabras y ordena por relevancia.
    """
    query = str(query or "").strip()
    try:
        limit = min(max(int(limit or DEFAULT_LIMIT), 1), MAX_LIMIT)
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    if len(query) < 2:
        return []

    with transaction_context() as db:
        if query.isdigit():
            rows = db.scalars(
                select(SatProductKey)
                .where(SatProductKey.clave.like(f"{query}%"))
                .order_by(SatProductKey.clave)
                .limit(limit)
            ).all()
            return [row.serialize() for row in rows]

        tokens = _tokenize(query)
        if not tokens:
            return []

        # El puntaje de cobertura se calcula en la base y ordena el SELECT. Es
        # indispensable: al ordenar por numero de clave, una coincidencia con
        # clave alta quedaba fuera de la ventana y no se veia nunca, aunque
        # fuera la correcta.
        coverage = None
        for token in tokens:
            term = case((_matches(token), 1), else_=0)
            coverage = term if coverage is None else coverage + term

        rows = db.scalars(
            select(SatProductKey)
            .where(or_(*[_matches(token) for token in tokens]))
            .order_by(coverage.desc(), SatProductKey.clave)
            .limit(max(limit * 6, 90))
        ).all()

        # Entre las mejores por cobertura se refina en Python: a igual
        # cobertura gana la palabra completa y la descripcion mas corta, que
        # suele ser la mas especifica.
        ordered = sorted(
            rows,
            key=lambda row: (-_relevance(row, tokens), len(row.description_norm or ""), row.clave),
        )
        return [row.serialize() for row in ordered[:limit]]


def catalog_status() -> dict:
    """Cuantas claves hay cargadas, para poder avisarlo en la interfaz."""
    with transaction_context() as db:
        total = db.scalar(select(func.count()).select_from(SatProductKey)) or 0
        return {"loaded": total > 0, "total": total}


def _normalize_header(value) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return stripped.strip().lower()


def _detect_columns(headers) -> tuple[int, int, int | None]:
    clave = description = keywords = None
    for index, header in enumerate(headers):
        name = _normalize_header(header)
        if clave is None and "clave" in name:
            clave = index
        elif description is None and "descrip" in name:
            description = index
        elif keywords is None and "palabra" in name:
            keywords = index
    if clave is None or description is None:
        raise ValueError(f"No se encontraron columnas de clave y descripcion. Encabezados: {headers}")
    return clave, description, keywords


def import_product_keys(csv_path) -> dict:
    """Carga o actualiza el catalogo desde el CSV oficial del SAT.

    Es idempotente y tolera el preambulo (titulo, version, fecha) que el
    archivo del SAT trae antes de los encabezados.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo {path}")

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        columns = None
        for _ in range(10):
            row = next(reader, None)
            if row is None:
                raise ValueError("El CSV esta vacio o no tiene fila de encabezados.")
            try:
                columns = _detect_columns(row)
                break
            except ValueError:
                continue
        if columns is None:
            raise ValueError("No se encontro la fila de encabezados en el CSV.")
        clave_index, description_index, keywords_index = columns

        with transaction_context() as db:
            # Se precargan las claves existentes para no consultar por fila:
            # con 52,000 renglones la diferencia es de minutos a segundos.
            existing = {row.clave: row for row in db.scalars(select(SatProductKey)).all()}
            created = updated = skipped = 0

            for row in reader:
                if len(row) <= clave_index:
                    continue
                clave = (row[clave_index] or "").strip()
                if not (clave.isdigit() and len(clave) == 8):
                    skipped += 1
                    continue
                description = (row[description_index] or "").strip()
                keywords = ""
                if keywords_index is not None and len(row) > keywords_index:
                    keywords = (row[keywords_index] or "").strip()

                record = existing.get(clave)
                if record:
                    record.description = description
                    record.keywords = keywords
                    record.description_norm = normalize_search_text(description)
                    record.keywords_norm = normalize_search_text(keywords)
                    updated += 1
                else:
                    db.add(SatProductKey(
                        clave=clave,
                        description=description,
                        keywords=keywords,
                        description_norm=normalize_search_text(description),
                        keywords_norm=normalize_search_text(keywords),
                    ))
                    created += 1
            db.flush()
            return {"created": created, "updated": updated, "skipped": skipped}
