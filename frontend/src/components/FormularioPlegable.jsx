import { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { ChevronDown, ChevronRight, Plus } from "lucide-react";
import { useI18n } from "../i18n";
import "../styles/formulario-plegable.css";

/**
 * El formulario de alta, plegado hasta que hace falta.
 *
 * Por qué
 * -------
 * En estas pantallas el formulario va ARRIBA y la lista debajo, y el
 * formulario ocupa lo que ocupa: en Familias son tres campos y dos botones
 * antes de ver el primer renglón, y en las que tienen diez campos la lista
 * empieza fuera de la pantalla. Pero a estas pantallas se entra sobre todo a
 * MIRAR —buscar una familia, comprobar una unidad—, y dar de alta es lo que se
 * hace de vez en cuando. Lo frecuente estaba pagando el sitio de lo raro.
 *
 * Plegado por omisión, entonces: se entra y se ve la lista. La cabecera es el
 * botón que lo abre, así que abrir cuesta un clic y no hay que aprender nada
 * nuevo —es el mismo renglón que ya estaba ahí, ahora pulsable—.
 *
 * Se abre solo al editar
 * ----------------------
 * `abrirSi` existe para eso. Sin él, pulsar el lápiz de un renglón cargaría el
 * formulario con esos datos... detrás de una cabecera cerrada: la pantalla no
 * haría nada visible y el usuario volvería a pulsar. Cuando `abrirSi` pasa a
 * tener valor —normalmente el id que se está editando— el formulario se abre
 * solo.
 *
 * Y no se cierra solo al terminar de editar, a propósito: quien acaba de dar
 * de alta algo suele dar de alta otra cosa, y cerrarle el formulario en la
 * cara le obliga a volver a abrirlo. Cerrar es decisión suya.
 *
 * `cerrarAlEnviar` es la única excepción a eso, y por lo mismo nace apagada
 * (`false`): un uso puntual (el editor de widgets del dashboard de KPIs,
 * donde SÍ conviene cerrar tras agregar un gráfico) puede pedirla explícito
 * sin cambiarle el comportamiento a ninguna de las otras pantallas que ya
 * usan este componente. Contrato: si se activa, `onSubmit` debe devolver la
 * promesa de su envío (no solo lanzarla sin esperar) -- el panel cierra
 * cuando esa promesa resuelve, y se queda abierto si rechaza, para que el
 * error quede a la vista sin obligar a reabrir.
 *
 * Animación de apertura/cierre
 * ----------------------------
 * El cuerpo sigue DESMONTÁNDOSE de verdad al cerrar -- el motivo de arriba
 * (un `required` escondido bloquearía el envío sin decir dónde) no cambia.
 * Lo que se anima es la transición: al abrir, el cuerpo se monta y el alto
 * crece con una transición CSS (`grid-template-rows`, sin medir nada en JS);
 * al cerrar, el alto baja a 0 primero y el desmontaje real ocurre en
 * `onTransitionEnd`, no de inmediato -- por eso hacen falta dos estados
 * (`abierto`, la intención; `montado`, si el cuerpo sigue en el DOM).
 *
 * Por que hace falta un TERCER estado (`asentado`)
 * -------------------------------------------------
 * La animacion de alto necesita `overflow: hidden` en el formulario y en el
 * wrapper del cuerpo MIENTRAS el renglon crece o se encoge -- si no, el
 * contenido se veria "salir" de golpe antes de que la fila termine de
 * crecer. El problema es dejar ese `overflow: hidden` puesto PARA SIEMPRE,
 * incluso ya abierto del todo: cualquier cosa que necesite salirse de su
 * caja (un popover, un `<select>` desplegado por el navegador con contenido
 * ancho, un dropdown propio) se ve cortada por ese mismo overflow, aunque el
 * renglon ya este a su altura final y no haya nada corriendose. Por eso
 * `overflow: hidden` solo se aplica MIENTRAS SE MUEVE (abriendo o cerrando):
 * `asentado` se vuelve `true` justo cuando la transicion de apertura
 * termina (mismo `onTransitionEnd` que ya existia para el desmontaje al
 * cerrar) y se apaga de inmediato en cuanto se empieza a cerrar -- ver
 * `.plegable-cuerpo-wrap.asentada` en formulario-plegable.css.
 */
export default function FormularioPlegable({
  titulo, abrirSi, onSubmit, icono: Icono, children, className, cerrarAlEnviar,
}) {
  const { t } = useI18n();
  const [abierto, setAbierto] = useState(false);
  const [montado, setMontado] = useState(false);
  const [asentado, setAsentado] = useState(false);
  const cuerpoWrapRef = useRef(null);

  function alternar() {
    setAbierto((antes) => {
      const siguiente = !antes;
      if (siguiente) setMontado(true);
      else setAsentado(false);
      return siguiente;
    });
  }

  // Solo al pasar de "nada" a "algo". Con `abrirSi` a secas en las
  // dependencias, cualquier render con el mismo valor volveria a abrirlo
  // despues de que el usuario lo cerrara a mano.
  const anterior = useRef(abrirSi);
  useEffect(() => {
    if (abrirSi && !anterior.current) {
      setAbierto(true);
      setMontado(true);
    }
    anterior.current = abrirSi;
  }, [abrirSi]);

  const alTerminarTransicion = useCallback((evento) => {
    // Se filtra el target: un elemento de adentro con su propia transicion
    // (un input, un boton) tambien dispara "transitionend" y burbujea hasta
    // aca -- solo importa la transicion del propio wrapper de alto.
    if (evento.target !== cuerpoWrapRef.current) return;
    setAbierto((sigueAbierto) => {
      if (!sigueAbierto) setMontado(false);
      else setAsentado(true);
      return sigueAbierto;
    });
  }, []);

  async function manejarEnvio(evento) {
    if (!cerrarAlEnviar) {
      onSubmit(evento);
      return;
    }
    evento.preventDefault();
    try {
      await onSubmit(evento);
      setAbierto(false);
    } catch {
      // onSubmit ya deja su propio mensaje de error en pantalla -- no se
      // cierra, para que se vea sin tener que volver a abrir.
    }
  }

  return (
    <form
      className={`form-card plegable ${abierto ? "abierta" : "cerrada"} ${className}`.trim()}
      onSubmit={manejarEnvio}
    >
      {/* La cabecera ES el botón. Un botón aparte al lado seria un objetivo
          pequeño junto a un renglón grande que no hace nada. */}
      <button
        type="button"
        className="form-header plegable-cabecera"
        onClick={alternar}
        aria-expanded={abierto}
      >
        {abierto ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <Icono size={18} />
        <strong>{titulo}</strong>
        <span className="muted plegable-pista">
          {abierto
            ? t("common.collapse_form", "ocultar")
            : t("common.expand_form", "abrir")}
        </span>
      </button>

      <div
        ref={cuerpoWrapRef}
        className={`plegable-cuerpo-wrap ${abierto ? "abierta" : ""} ${asentado ? "asentada" : ""}`}
        onTransitionEnd={alTerminarTransicion}
      >
        {/* Se desmonta en lugar de esconderse con CSS: escondido, sus campos
            siguen en el formulario y un `required` invisible bloquea el envio
            sin decir donde. Y aqui dentro no hay estado que perder -- lo
            tiene la pantalla, no el formulario. */}
        {montado && <div className="plegable-cuerpo">{children}</div>}
      </div>
    </form>
  );
}

FormularioPlegable.propTypes = {
  titulo: PropTypes.node.isRequired,
  // Lo que fuerza la apertura: normalmente el id que se esta editando.
  abrirSi: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.bool]),
  onSubmit: PropTypes.func.isRequired,
  icono: PropTypes.elementType,
  children: PropTypes.node,
  className: PropTypes.string,
  cerrarAlEnviar: PropTypes.bool,
};

FormularioPlegable.defaultProps = {
  abrirSi: null,
  icono: Plus,
  children: null,
  className: "",
  cerrarAlEnviar: false,
};
