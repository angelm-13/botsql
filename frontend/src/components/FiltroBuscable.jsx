import PropTypes from "prop-types";
import { useId, useMemo } from "react";
import { useI18n } from "../i18n";
import "../styles/filtro-buscable.css";

/**
 * Un filtro con muchas opciones, en un solo control.
 *
 * Por qué existe
 * --------------
 * Medido con los 2 221 productos importados, los filtros de Localizar ofrecen
 * 146 familias, 84 marcas y 562 materiales. Un `<select>` plano de 562 opciones
 * no es un filtro: es una lista donde hay que bajar con la rueda buscando a
 * ojo, y ordenar alfabéticamente no ayuda cuando no recuerdas si el material se
 * llamó «ARCO CON SEGUETA» o «SEGUETA, ARCO».
 *
 * Un solo control, no dos
 * -----------------------
 * La primera versión ponía una caja de texto ENCIMA del select. Funcionaba y
 * sobraba: cuatro filtros son cuatro cajas de más en una barra que se mira todo
 * el día. Ahora es un `<input list>` con su `<datalist>`: el mismo campo donde
 * se lee la opción elegida es donde se escribe para buscarla, y el type-ahead
 * lo hace el navegador.
 *
 * Las etiquetas repetidas
 * -----------------------
 * Un `<datalist>` resuelve la opción por su ETIQUETA, no por su identificador, y
 * en estos datos hay 199 materiales con la descripción repetida — «dado 1 1/8»
 * aparece cinco veces. Así que cuando dos opciones comparten etiqueta se les
 * añade su identificador: sin eso, elegir una de las cinco daría siempre la
 * primera.
 */

export default function FiltroBuscable({
  valor, opciones, onChange, etiqueta, todas,
}) {
  const { t } = useI18n();
  const idLista = useId();

  // Etiquetas únicas. Dos opciones con el mismo texto son indistinguibles para
  // un datalist, y elegir la segunda devolvería la primera.
  const { porEtiqueta, etiquetaDe } = useMemo(() => {
    const cuantas = new Map();
    opciones.forEach((o) => {
      const clave = String(o.label || "");
      cuantas.set(clave, (cuantas.get(clave) || 0) + 1);
    });
    const mapa = new Map();
    const inverso = new Map();
    opciones.forEach((o) => {
      const base = String(o.label || "");
      const unica = cuantas.get(base) > 1 ? `${base} · #${o.value}` : base;
      mapa.set(unica, String(o.value));
      inverso.set(String(o.value), unica);
    });
    return { porEtiqueta: mapa, etiquetaDe: inverso };
  }, [opciones]);

  const textoActual = valor ? (etiquetaDe.get(String(valor)) || "") : "";

  const elegir = (escrito) => {
    const limpio = String(escrito || "").trim();
    if (!limpio) {
      onChange("");
      return;
    }
    const exacta = porEtiqueta.get(limpio);
    if (exacta !== undefined) {
      onChange(exacta);
      return;
    }
    // Sin coincidencia exacta se busca una sola parcial: escribir "segueta" y
    // que quede una es el caso normal, y obligar a completar el texto entero
    // sería pedir que uno se acuerde de cómo se escribió.
    const aguja = limpio.toLowerCase();
    const parciales = [...porEtiqueta.entries()]
      .filter(([nombre]) => nombre.toLowerCase().includes(aguja));
    if (parciales.length === 1) onChange(parciales[0][1]);
  };

  return (
    <label className="filtro-buscable">
      <input
        list={idLista}
        defaultValue={textoActual}
        key={textoActual}
        placeholder={todas}
        aria-label={etiqueta}
        onChange={(e) => {
          // Al elegir del desplegable el navegador escribe la etiqueta entera
          // de golpe: se aplica ahí y no al salir del campo, para que un clic
          // en la opción filtre sin pedir un paso más.
          if (porEtiqueta.has(e.target.value.trim())) elegir(e.target.value);
        }}
        onBlur={(e) => elegir(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            elegir(e.currentTarget.value);
          }
        }}
      />
      <datalist id={idLista}>
        {[...porEtiqueta.keys()].map((nombre) => (
          <option key={nombre} value={nombre} />
        ))}
      </datalist>
      {/* Cuántas hay detrás. Sin esto no se sabe si el campo vacío significa
          "todas" o "el catálogo está vacío". */}
      <span className="filtro-buscable-cuenta muted">
        {opciones.length} {t("common.options", "opciones")}
      </span>
    </label>
  );
}

FiltroBuscable.propTypes = {
  valor: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  opciones: PropTypes.arrayOf(PropTypes.shape({
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    label: PropTypes.string,
  })).isRequired,
  onChange: PropTypes.func.isRequired,
  etiqueta: PropTypes.string.isRequired,
  todas: PropTypes.string.isRequired,
};

FiltroBuscable.defaultProps = {
  valor: "",
};
