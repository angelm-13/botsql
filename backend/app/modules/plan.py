"""El plan del despliegue: que modulos compro este cliente.

Por que existe
--------------
TYAKXA es el software completo, pero se vende por partes. Un cliente compra
inventario y punto de venta; otro, facturacion, restaurante e inventario. Cada
despliegue es una copia del mismo codigo con un plan distinto.

El plan es la capa de arriba de tres, y conviene tenerlas separadas en la
cabeza:

    plan     -> que modulos existen en este despliegue   (lo emitimos nosotros)
    rol      -> que puede hacer un puesto de lo que hay  (lo reparte el cliente)
    alcance  -> a que datos llega                        (proyecto, sucursal)

La regla que las une: **el rol nunca concede por encima del plan.** El
administrador del cliente reparte permisos con libertad, pero solo entre los
modulos que compro. Un modulo fuera del plan no se le niega al usarlo: no
existe para concederlo.

De donde sale el plan
---------------------
De la configuracion del despliegue, en dos formas que se complementan:

* **`LICENSED_MODULES`**: la lista de modulos, separada por comas. Es la que ya
  usan los tres ambientes reales y la que el sembrado consulta al aplicarse
  (`psql -v licensed_modules=...`, ver `k8s/base/backend.yaml`). Manda sobre los
  modulos.
* **`TYAKXA_PLAN`**: el JSON completo, con el nombre del cliente y los topes que
  `LICENSED_MODULES` no puede expresar -usuarios, almacenamiento-. Tambien
  acepta `modulos`, que se usa solo si `LICENSED_MODULES` no viene.

Dos variables y no una porque hacen falta las dos cosas y `LICENSED_MODULES` ya
estaba desplegada: cambiarle la forma habria obligado a tocar tres ambientes en
produccion para ganar elegancia. La forma del JSON es la que tendra la licencia
firmada, para que cuando llegue solo cambie de donde se lee el dato.

* **`DEPLOYMENT_LABEL`**: nombre o abreviacion del cliente, solo para pantalla
  -que no se confunda un despliegue con otro-. Aparte de las dos anteriores
  porque no es un control de acceso: no deberia hacer falta escribir el JSON
  completo del plan solo para poner un nombre. Si `TYAKXA_PLAN` ya trae
  `cliente`, ese gana.

Un mecanismo, dos sitios donde se aplica
----------------------------------------
La misma declaracion gobierna el sembrado y las peticiones. El sembrado recorta
las filas que existen; los guardias niegan lo que no este en el plan aunque la
fila exista. Lo segundo hace falta porque el administrador del cliente tiene el
gestor de roles: sin el guardia, se concede a si mismo un modulo que no compro y
funciona.

    {
      "cliente": "Restaurante La Parroquia SA de CV",
      "modulos": ["facturacion", "inventario", "restaurante"],
      "limites": {"usuarios": 15, "almacenamiento_gb": 20}
    }

Mientras no haya licencia firmada, el plan se puede ampliar editando la
configuracion del servidor. Eso es una limitacion conocida, no un descuido: la
firma es el paso siguiente y esta capa se escribio para recibirla.

Dos decisiones que conviene conocer
-----------------------------------
**Un modulo desconocido en el plan detiene el arranque.** Un nombre mal escrito
-`facturacio`- dejaria ese modulo apagado sin que nadie se enterase, y el cliente
descubriria que no compro lo que compro al usarlo. Vale mas no arrancar.

**Configuracion y seguridad estan siempre encendidos.** No son modulos de
negocio que se vendan: son la infraestructura. Sin `status` ni `theme` los
desplegables de cada pantalla quedan vacios, y sin `user` ni `permission` nadie
puede administrar nada. Apagarlos por plan seria vender un sistema que no
enciende.

**Sin plan configurado, todo esta habilitado.** Es el comportamiento de un
despliegue nuestro y de las pruebas. No es el que debe tener una instalacion de
cliente: ahi el plan se pone siempre, y al arrancar se escribe en la bitacora
cual quedo activo para que no haya duda.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib

from app.modules.registry import MODULOS, MODULOS_DE_NEGOCIO, modulo_de


registro = logging.getLogger(__name__)

# Los que no se venden porque sin ellos no hay sistema. Ver el encabezado.
MODULOS_SIEMPRE = frozenset({"configuracion", "seguridad"})

CLAVES_VALIDAS = frozenset(m.clave for m in MODULOS)

LIMITES_POR_OMISION = {
    "usuarios": None,          # None significa sin tope
    "almacenamiento_gb": None,
}


class PlanInvalido(RuntimeError):
    """El plan configurado no se puede aplicar, asi que el servidor no arranca."""


class Plan:
    """Lo que este despliegue tiene habilitado."""

    def __init__(self, datos: dict | None):
        datos = datos or {}
        self.cliente = str(datos.get("cliente") or "").strip() or None
        self.tipo = str(datos.get("tipo") or "completa").strip().lower()
        self.completo = "modulos" not in datos

        if self.completo:
            declarados = set(MODULOS_DE_NEGOCIO)
        else:
            crudos = datos.get("modulos") or []
            if not isinstance(crudos, (list, tuple)):
                raise PlanInvalido("`modulos` debe ser una lista de claves de modulo")
            declarados = {str(c).strip().lower() for c in crudos if str(c).strip()}
            desconocidos = sorted(declarados - CLAVES_VALIDAS)
            if desconocidos:
                # Un nombre mal escrito apagaria ese modulo en silencio.
                raise PlanInvalido(
                    "modulos desconocidos en el plan: " + ", ".join(desconocidos)
                    + " | validos: " + ", ".join(sorted(CLAVES_VALIDAS))
                )

        self.modulos = frozenset(declarados) | MODULOS_SIEMPRE

        # Se comprueba el tipo ANTES de sustituir por vacio: `"limites": []` es
        # falso, asi que con `or {}` se colaba como "sin topes" en vez de
        # reportarse. Un plan escrito con la forma equivocada es un error de
        # quien lo emitio y hay que verlo.
        limites = datos.get("limites")
        if limites is not None and not isinstance(limites, dict):
            raise PlanInvalido("`limites` debe ser un objeto")
        limites = limites or {}
        self.limites = {**LIMITES_POR_OMISION, **limites}

    def __repr__(self):
        return f"<Plan {'completo' if self.completo else sorted(self.modulos)}>"

    def modulo_habilitado(self, clave) -> bool:
        return str(clave or "") in self.modulos

    def entidad_habilitada(self, nombre) -> bool:
        """Si la entidad o capacidad pertenece a un modulo del plan.

        Una entidad que el registro no conoce se deja pasar: el plan no puede
        ser la razon por la que algo sin modulo declarado deje de funcionar. El
        registro ya se valida por su cuenta al importar, y las pruebas fijan que
        toda entidad protegida tenga su modulo.
        """
        clave = modulo_de(nombre)
        if clave is None:
            return True
        return clave in self.modulos

    def limite(self, nombre, por_omision=None):
        valor = self.limites.get(nombre, por_omision)
        return por_omision if valor is None else valor

    def serialize(self) -> dict:
        return {
            "cliente": self.cliente,
            "tipo": self.tipo,
            "completo": self.completo,
            "modulos": sorted(self.modulos),
            "limites": dict(self.limites),
        }


def _modulos_licenciados() -> list[str] | None:
    """`LICENSED_MODULES` del despliegue, o None si no viene.

    Vacia y ausente significan lo mismo -todos los modulos-, igual que en el
    sembrado: una instalacion que nunca la configuro sigue viendo todo.
    """
    crudo = (os.getenv("LICENSED_MODULES") or "").strip()
    if not crudo:
        return None
    claves = [c.strip().lower() for c in crudo.split(",") if c.strip()]
    return claves or None


def _etiqueta_del_despliegue() -> str:
    """`DEPLOYMENT_LABEL`: el nombre o abreviacion del cliente, para pantalla.

    Aparte de `LICENSED_MODULES`/`TYAKXA_PLAN` a proposito: es una etiqueta
    visual -que cliente es este despliegue-, sin nada que ver con permisos, y
    exigir el JSON completo del plan solo para poner un nombre habria sido
    friccion de mas para algo que hoy ningun ambiente real usa.
    """
    return (os.getenv("DEPLOYMENT_LABEL") or "").strip()


def _leer_configuracion() -> dict | None:
    """El plan tal como lo dejo el despliegue, sin interpretarlo."""
    ruta = (os.getenv("TYAKXA_PLAN_FILE") or "").strip()
    if ruta:
        archivo = pathlib.Path(ruta)
        if not archivo.is_file():
            raise PlanInvalido(f"TYAKXA_PLAN_FILE apunta a un archivo que no existe: {ruta}")
        crudo = archivo.read_text(encoding="utf-8")
    else:
        crudo = (os.getenv("TYAKXA_PLAN") or "").strip()

    licenciados = _modulos_licenciados()
    etiqueta = _etiqueta_del_despliegue()

    if not crudo:
        # Sin JSON pero con LICENSED_MODULES y/o DEPLOYMENT_LABEL: se arma un
        # plan minimo con lo que haya, sin topes.
        if licenciados is None and not etiqueta:
            return None
        datos = {}
        if licenciados is not None:
            datos["modulos"] = licenciados
        if etiqueta:
            datos["cliente"] = etiqueta
        return datos
    try:
        datos = json.loads(crudo)
    except json.JSONDecodeError as error:
        raise PlanInvalido(f"el plan no es JSON valido: {error}") from error
    if not isinstance(datos, dict):
        raise PlanInvalido("el plan debe ser un objeto JSON")

    # `LICENSED_MODULES` manda sobre los modulos: es la que el sembrado consulta
    # al aplicarse, y si las dos dijeran cosas distintas las filas sembradas y
    # lo que los guardias permiten dejarian de coincidir. Un modulo con filas
    # que nadie puede usar, o al contrario, es peor que cualquiera de los dos
    # recortes por separado.
    if licenciados is not None:
        datos = {**datos, "modulos": licenciados}
    # Aqui SI gana lo que ya traiga el plan: cuando llegue la licencia firmada
    # con su propio `cliente`, ese es el dato de verdad. DEPLOYMENT_LABEL es
    # el respaldo de mientras tanto, no algo que deba pisarlo.
    if etiqueta and not str(datos.get("cliente") or "").strip():
        datos = {**datos, "cliente": etiqueta}
    return datos


_plan: Plan | None = None


def plan_actual() -> Plan:
    """El plan de este despliegue, leido una sola vez."""
    global _plan
    if _plan is None:
        _plan = Plan(_leer_configuracion())
        if _plan.completo:
            registro.info(
                "Sin plan configurado: todos los modulos de negocio habilitados. "
                "Una instalacion de cliente debe declarar TYAKXA_PLAN."
            )
        else:
            registro.info(
                "Plan activo%s: %s",
                f" de {_plan.cliente}" if _plan.cliente else "",
                ", ".join(sorted(_plan.modulos)),
            )
    return _plan


def reiniciar_plan() -> None:
    """Vuelve a leer la configuracion. Solo para pruebas."""
    global _plan
    _plan = None


# --- atajos, que es como se usa desde el resto del codigo -------------------

def modulo_habilitado(clave) -> bool:
    return plan_actual().modulo_habilitado(clave)


def entidad_habilitada(nombre) -> bool:
    return plan_actual().entidad_habilitada(nombre)


def limite(nombre, por_omision=None):
    return plan_actual().limite(nombre, por_omision)
