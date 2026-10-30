"""Un reloj congelado para las pruebas que dependen de "ahora" (`app.utils.tiempo.ahora_negocio`)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


@contextmanager
def reloj_en_utc(instante_utc: datetime):
    """Congela `datetime.now(...)` de `app.utils.tiempo` en un instante UTC.

    `ahora_negocio()` sigue convirtiendo con `ZONA_NEGOCIO`: lo que se prueba es esa conversion real, no una
    hora local escrita a mano.
    """
    fijo = instante_utc.replace(tzinfo=timezone.utc)

    class _Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return fijo.astimezone(tz) if tz else fijo.replace(tzinfo=None)

    with patch("app.utils.tiempo.datetime", _Reloj):
        yield


def ahora_local(hora_local: datetime):
    """El mismo reloj, dado en hora de Mexico (UTC-6 todo el ano desde 2022): las 15:00 locales son las 21:00 UTC."""
    return reloj_en_utc(hora_local + timedelta(hours=6))
