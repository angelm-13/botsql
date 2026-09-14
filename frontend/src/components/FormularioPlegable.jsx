import { useEffect, useRef, useState } from "react";
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
 */
export default function FormularioPlegable({
  titulo, abrirSi, onSubmit, icono: Icono, children, className,
}) {
  const { t } = useI18n();
  const [abierto, setAbierto] = useState(false);

  // Solo al pasar de "nada" a "algo". Con `abrirSi` a secas en las
  // dependencias, cualquier render con el mismo valor volveria a abrirlo
  // despues de que el usuario lo cerrara a mano.
  const anterior = useRef(abrirSi);
  useEffect(() => {
    if (abrirSi && !anterior.current) setAbierto(true);
    anterior.current = abrirSi;
  }, [abrirSi]);

  return (
    <form
      className={`form-card plegable ${abierto ? "abierta" : "cerrada"} ${className}`.trim()}
      onSubmit={onSubmit}
    >
      {/* La cabecera ES el botón. Un botón aparte al lado seria un objetivo
          pequeño junto a un renglón grande que no hace nada. */}
      <button
        type="button"
        className="form-header plegable-cabecera"
        onClick={() => setAbierto((antes) => !antes)}
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

      {/* Se desmonta en lugar de esconderse con CSS: escondido, sus campos
          siguen en el formulario y un `required` invisible bloquea el envio sin
          decir donde. Y aqui dentro no hay estado que perder -- lo tiene la
          pantalla, no el formulario. */}
      {abierto && <div className="plegable-cuerpo">{children}</div>}
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
};

FormularioPlegable.defaultProps = {
  abrirSi: null,
  icono: Plus,
  children: null,
  className: "",
};
