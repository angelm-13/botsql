import PropTypes from "prop-types";
import "../styles/page-header.css";

/**
 * La cabecera de una pantalla: de dónde es, cómo se llama y para qué sirve.
 *
 * Por qué un componente y no una clase de CSS
 * -------------------------------------------
 * La clase sola no impedía que cada pantalla armara el bloque a su manera, y
 * es lo que pasó: 60 pantallas con `<h2>` y sin subtítulo, 8 con `<h1>` y
 * subtítulo, y de esas 8 tres traían su propia copia de la misma regla de
 * CSS. El mismo encabezado escrito de cuatro maneras se ve de cuatro maneras.
 *
 * Con el componente hay un solo sitio donde cambia el orden de las piezas, un
 * solo `<h1>` por pantalla —que es lo correcto para un lector de pantalla: el
 * título de la página no es un subtítulo de nada— y un solo lugar donde
 * ponerle algo nuevo a todas.
 *
 * El subtítulo es opcional a propósito: es mejor no tenerlo que tener uno que
 * repita el título con otras palabras.
 */
export default function PageHeader({ eyebrow, titulo, subtitulo, children }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{titulo}</h1>
        {subtitulo && <p className="page-header-sub">{subtitulo}</p>}
      </div>
      {children && <div className="page-header-acciones">{children}</div>}
    </header>
  );
}

PageHeader.propTypes = {
  eyebrow: PropTypes.node,
  titulo: PropTypes.node.isRequired,
  subtitulo: PropTypes.node,
  children: PropTypes.node,
};

PageHeader.defaultProps = {
  eyebrow: null,
  subtitulo: null,
  children: null,
};
