"""La frontera con el modelo de lenguaje.

Todo lo que el resto del modulo sabe del modelo es esta interfaz. Eso es lo
que hace que el desacople sea real y no de nombre:

  * El extractor, el validador, el ejecutor y la API corren y se prueban sin
    Ollama instalado, sin GPU y sin red.
  * Cambiar Ollama por vLLM, por llama.cpp o por un servicio propio es
    escribir una clase de veinte lineas. No se toca nada mas.
  * `ProveedorDeGuion` devuelve JSON fijo: las pruebas de seguridad y de
    ejecucion no dependen de que un modelo acierte.

Se usa `urllib` de la biblioteca estandar a proposito: el modulo no agrega
una dependencia mas para una sola llamada POST.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field


def _normalizar(texto: str) -> str:
    """Minusculas y sin acentos, para comparar como escribe la gente."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return sin_tildes


@dataclass(frozen=True)
class RespuestaLLM:
    texto: str
    modelo: str
    ms: int
    tokens_prompt: int = 0
    tokens_respuesta: int = 0


class ProveedorNoDisponible(Exception):
    """No hay modelo configurado, o no contesto a tiempo."""


class ProveedorLLM:
    """Interfaz. Una implementacion recibe el prompt y devuelve texto crudo."""

    nombre = "ninguno"

    def generar(self, prompt: str, pregunta: str = "", formato=None) -> RespuestaLLM:
        """`prompt` es el contrato completo; `pregunta` es solo lo que
        escribio la persona. Se pasan por separado porque un proveedor
        de chat las mandaria en roles distintos (sistema / usuario), y
        porque buscar la pregunta dentro del prompt no funciona: el
        contrato ya contiene palabras como "dashboard"."""
        raise ProveedorNoDisponible("No hay un modelo de lenguaje configurado.")

    def disponible(self) -> bool:
        return False


@dataclass
class ProveedorDeGuion(ProveedorLLM):
    """Devuelve respuestas de un guion fijo. Para pruebas y demostraciones.

    No simula un modelo: simula que YA contesto, para poder probar todo lo
    que viene despues -- parseo, validacion, ejecucion, formato -- sin
    inferencia de por medio.
    """

    guion: dict[str, str] = field(default_factory=dict)
    respuesta_fija: str | None = None
    nombre: str = "guion"
    llamadas: list[str] = field(default_factory=list)
    # Que se contesta cuando la pregunta no esta en el guion. Sin
    # `respuesta_fija`, lo honesto es decirlo: un guion que devuelve siempre
    # algo aparenta entender preguntas que no entiende.
    mensaje_sin_guion: str = "El guion no tiene respuesta para esta pregunta."

    def generar(self, prompt: str, pregunta: str = "", formato=None) -> RespuestaLLM:
        self.llamadas.append(prompt)
        # Se busca en la PREGUNTA, no en el prompt: el prompt trae el
        # contrato entero y cualquier clave coincidiria siempre.
        #
        # La coincidencia ancla al INICIO de palabra, no a cualquier parte:
        # con subcadena suelta, la clave "mes" se dispara dentro de
        # "tri-mes-tre", y una pregunta que el guion no cubre acaba
        # contestada
        # con una grafica que no viene a cuento -- aparentando que entendio.
        # Anclar solo al inicio (y no tambien al final) deja que "producto"
        # siga cazando "productos", que es lo que la gente escribe.
        texto = _normalizar(pregunta or "")
        for clave, respuesta in self.guion.items():
            if re.search(rf"\b{re.escape(_normalizar(clave))}", texto):
                return RespuestaLLM(texto=respuesta, modelo="guion", ms=0)
        if self.respuesta_fija is None:
            raise ProveedorNoDisponible(self.mensaje_sin_guion)
        return RespuestaLLM(texto=self.respuesta_fija, modelo="guion", ms=0)

    def disponible(self) -> bool:
        return True


# Esquema JSON que Ollama usa para RESTRINGIR la generacion (decodificacion
# guiada por gramatica): el modelo no puede emitir texto fuera de este contrato
# ni dejar el JSON a medias. Con `format: "json"` a secas, un 3B a veces se
# iba hasta el tope de tokens sin cerrar el objeto (medido: 700 tokens, sin JSON).
_VIS = {
    "type": "object",
    "properties": {
        "recommended": {"type": "boolean"},
        "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "area", "kpi_card", "table"]},
        "title": {"type": "string"},
        "x_axis": {"type": "string"},
        "y_axis": {"type": "string"},
        "metric_label": {"type": "string"},
    },
    "required": ["chart_type", "title"],
}
ESQUEMA_DE_RESPUESTA = {
    "type": "object",
    "properties": {
        "is_dashboard": {"type": "boolean"},
        "dashboard_title": {"type": "string"},
        "sql_query": {"type": "string"},
        "explanation": {"type": "string"},
        "visualization": _VIS,
        "widgets": {"type": "array", "items": {
            "type": "object",
            "properties": {"sql_query": {"type": "string"}, "explanation": {"type": "string"},
                           "visualization": _VIS},
            "required": ["sql_query", "visualization"]}},
        "error": {"type": "string"},
    },
    "required": ["is_dashboard"],
}

# Contrato de una pregunta normal: solo el SQL. Titulo, explicacion y grafica los decide el
# servidor, asi que no se le pide nada de eso al modelo: cada token de salida cuesta entre
# 0.25 y 1 s en CPU. Los dos campos son opcionales para que pueda negarse con
# {"error": ...} (regla 1 del prompt).
ESQUEMA_CONSULTA = {
    "type": "object",
    "properties": {"sql_query": {"type": "string"}, "error": {"type": "string"}},
}


class ProveedorOllama(ProveedorLLM):
    """Habla con un Ollama local por HTTP.

    Tres opciones que no son de adorno:

    * `format: "json"` hace que Ollama restrinja la generacion a JSON valido.
      No garantiza que el JSON tenga la forma que queremos -- de eso se
      encarga `directive.py` -- pero elimina de golpe el modo de falla mas
      comun, que es el modelo envolviendo el JSON en prosa.
    * `temperature: 0`. Para traducir a SQL no se quiere creatividad: se
      quiere la misma respuesta cada vez, que ademas es lo que hace util
      cualquier cache aguas arriba.
    * `keep_alive: -1` deja el modelo cargado en memoria. Sin esto, la
      primera pregunta despues de un rato de inactividad paga otra vez la
      carga a RAM -- entre diez y veinte segundos que el usuario percibe
      como "a veces se traba".
    """

    nombre = "ollama"

    def __init__(
        self,
        url: str = "http://localhost:11434",
        # El tag debe ser EXACTO al que se descargo con `ollama pull`.
        # "qwen2.5-coder:7b" y "qwen2.5-coder:7b-instruct" son el mismo
        # modelo en el registro, pero Ollama los trata como pulls distintos:
        # pedir uno que no se bajo falla en la generacion aunque /api/tags
        # muestre el otro como disponible.
        modelo: str = "qwen2.5-coder:7b",
        # Medido real, sin GPU: una pregunta libre de este modulo tardo
        # 90-100s de punta a punta en CPU pura, y 166s dentro de Docker con
        # otros contenedores compitiendo por CPU. Con GPU baja a segundos.
        timeout: int = 600,
        temperatura: float = 0.0,
        num_ctx: int = 4096,
        num_hilos: int = 0,
    ):
        self.url = url.rstrip("/")
        self.modelo = modelo
        self.timeout = timeout
        self.temperatura = temperatura
        self.num_ctx = num_ctx
        self.num_hilos = num_hilos

    def _opciones(self, num_predict: int) -> dict:
        # Las mismas en toda llamada, incluido el precalentamiento: si `num_ctx` o
        # `num_thread` cambian entre dos peticiones, Ollama recarga el modelo y pierde
        # la memoria del prefijo que se queria reutilizar.
        return {
            "temperature": self.temperatura,
            # El DDL de un ERP mediano ya son varios miles de tokens; con
            # la ventana por omision de Ollama (2048) el esquema se
            # trunca en silencio y el modelo inventa columnas.
            "num_ctx": self.num_ctx,
            "num_predict": num_predict,
            **({"num_thread": self.num_hilos} if self.num_hilos else {}),
        }

    def calentar(self, prefijo: str) -> int | None:
        """Carga el modelo y deja leido `prefijo` (la parte fija del prompt).

        Se llama una vez al arrancar, en un hilo. Sin esto la primera pregunta del dia
        paga la carga del modelo a RAM (10-20 s) y la lectura de todo el prompt; con
        esto solo paga lo que cambia. Devuelve los ms que tardo, o None si Ollama no
        contesto -- calentar es una cortesia, nunca debe tumbar el arranque.
        """
        cuerpo = json.dumps({
            "model": self.modelo, "prompt": prefijo, "stream": False,
            "keep_alive": -1, "options": self._opciones(1),
        }).encode("utf-8")
        peticion = urllib.request.Request(f"{self.url}/api/generate", data=cuerpo,
                                          headers={"Content-Type": "application/json"})
        inicio = time.monotonic()
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as r:
                r.read()
        except Exception:
            return None
        return int((time.monotonic() - inicio) * 1000)

    def generar(self, prompt: str, pregunta: str = "", formato=None) -> RespuestaLLM:
        cuerpo = json.dumps({
            "model": self.modelo,
            "prompt": prompt,
            "stream": False,
            "format": formato or ESQUEMA_DE_RESPUESTA,
            "keep_alive": -1,
            "options": self._opciones(500),
        }).encode("utf-8")

        peticion = urllib.request.Request(
            f"{self.url}/api/generate",
            data=cuerpo,
            headers={"Content-Type": "application/json"},
        )

        inicio = time.monotonic()
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as r:
                datos = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProveedorNoDisponible(f"Ollama no contesto: {exc}") from exc
        except ValueError as exc:
            raise ProveedorNoDisponible(f"Ollama contesto algo que no es JSON: {exc}") from exc

        ms = int((time.monotonic() - inicio) * 1000)
        texto = (datos.get("response") or "").strip()
        if not texto:
            raise ProveedorNoDisponible("Ollama devolvio una respuesta vacia.")

        return RespuestaLLM(
            texto=texto,
            modelo=self.modelo,
            ms=ms,
            tokens_prompt=int(datos.get("prompt_eval_count") or 0),
            tokens_respuesta=int(datos.get("eval_count") or 0),
        )

    def disponible(self) -> bool:
        """Si Ollama esta arriba Y el modelo esta descargado.

        Se distingue a proposito de "esta arriba": el error mas frecuente al
        estrenar el modulo es que Ollama corre pero nadie hizo `ollama pull`,
        y el mensaje que da la API en ese caso no lo dice claro.
        """
        try:
            with urllib.request.urlopen(f"{self.url}/api/tags", timeout=5) as r:
                datos = json.loads(r.read().decode("utf-8"))
        except Exception:
            return False
        nombres = {m.get("name", "") for m in datos.get("models", [])}
        base = self.modelo.split(":")[0]
        return any(n == self.modelo or n.split(":")[0] == base for n in nombres)
