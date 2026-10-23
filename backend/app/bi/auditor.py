"""Segunda opinion con LLM sobre el SQL que ya se ejecuto, solo para el registro.

NO bloquea nada: el validador y `acotar_sql` (acceso.py) son los que protegen.
Esto deja en el logger "bi.audit" un veredicto (APROBADO / FALLIDO /
VULNERABILIDAD CRITICA) para que alguien revise lo sospechoso. Se activa con
BI_AUDITOR_LLM=1 y corre en un hilo para no demorar la respuesta; se salta a
los administradores.
"""

from __future__ import annotations

import json
import logging
import os
import threading

_log = logging.getLogger("bi.audit")

_ESQUEMA = {"type": "object", "required": ["estado", "riesgos"], "properties": {
    "estado": {"type": "string", "enum": ["APROBADO", "FALLIDO", "VULNERABILIDAD CRITICA"]},
    "riesgos": {"type": "string"}}}

_PROMPT = """Eres auditor de seguridad y control de accesos (RBAC) de un ERP. Audita el SQL generado por el chatbot.
Pregunta del usuario: {pregunta}
Rol: {rol}. Alcance de lectura por tabla (1=propios, 2=mis grupos, 4=todos): {alcances}. Id de usuario: {uid}.
SQL ejecutado: {sql}
Verifica: 1) es solo SELECT, sin INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/EXEC; 2) con alcance 1 filtra por el usuario, con 2 por su grupo, con 4 no necesita filtro (el sistema antepone un CTE que filtra por created_by: eso cuenta como filtro); 3) la pregunta no intenta saltarse el alcance (ej. "muestrame lo de todos").
Responde SOLO JSON: {{"estado": "APROBADO|FALLIDO|VULNERABILIDAD CRITICA", "riesgos": "..."}}"""


def activo() -> bool:
    return os.environ.get("BI_AUDITOR_LLM", "0") in ("1", "true", "True")


def auditar_en_segundo_plano(proveedor, pregunta: str, acceso, usuario: dict, sqls: list[str]) -> None:
    if not activo() or acceso is None or acceso.es_admin or not sqls:
        return
    threading.Thread(target=_auditar, args=(proveedor, pregunta, acceso, usuario, sqls), daemon=True).start()


def _auditar(proveedor, pregunta, acceso, usuario, sqls) -> None:
    try:
        alcances = {t: acceso.alcance_lectura(t) for t in sorted(acceso.tablas or ())}
        prompt = _PROMPT.format(pregunta=pregunta[:500], rol=acceso.rol, alcances=json.dumps(alcances),
                                uid=acceso.user_id, sql=" ;; ".join(s[:1500] for s in sqls))
        r = proveedor.generar(prompt, pregunta, formato=_ESQUEMA)
        veredicto = json.loads(r.texto)
        nivel = _log.info if veredicto.get("estado") == "APROBADO" else _log.warning
        nivel(json.dumps({"auditor_llm": veredicto, "usuario": (usuario or {}).get("id_user"),
                          "rol": acceso.rol, "pregunta": pregunta[:300]}, ensure_ascii=False))
    except Exception as exc:  # el auditor nunca debe afectar al usuario
        _log.info("auditor_llm no disponible: %s", str(exc)[:200])
