import { useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";

/**
 * Una persona: alguien del sistema, o un externo escrito a mano.
 *
 * Conforme se escribe filtra los usuarios por nombre; si ninguno es, la ultima
 * opcion es usar lo escrito como persona EXTERNA (chofer, mensajero). El valor
 * es `{ id_user, name }` y siempre uno de los dos esta vacio -- el servidor
 * tambien lo exige (`errors.voucher_pickup_conflict`).
 */
const MAX_OPCIONES = 8;

const sinAcentos = (texto) =>
  String(texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const nombreDe = (u) => u.full_name || u.username || `#${u.id_user}`;

export default function PersonaCombobox({
  usuarios, valor, onChange, vacio, etiquetaExterno, etiquetaYo, idYo, id,
}) {
  const [texto, setTexto] = useState("");
  const [abierto, setAbierto] = useState(false);
  const raiz = useRef(null);

  const seleccionada = valor?.id_user
    ? usuarios.find((u) => Number(u.id_user) === Number(valor.id_user))
    : null;

  // Cierra al hacer clic fuera.
  useEffect(() => {
    if (!abierto) return undefined;
    const fuera = (e) => { if (raiz.current && !raiz.current.contains(e.target)) setAbierto(false); };
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);

  const coincidencias = useMemo(() => {
    const buscado = sinAcentos(texto.trim());
    const todos = buscado
      ? usuarios.filter((u) => sinAcentos(nombreDe(u)).includes(buscado))
      : usuarios;
    return todos.slice(0, MAX_OPCIONES);
  }, [usuarios, texto]);

  const limpio = texto.trim();
  // "Usar X como externo" solo si lo escrito no es exactamente un usuario.
  const ofreceExterno = limpio.length >= 2 && !usuarios.some(
    (u) => sinAcentos(nombreDe(u)) === sinAcentos(limpio));

  const elegirUsuario = (u) => {
    onChange({ id_user: String(u.id_user), name: "" });
    setTexto(""); setAbierto(false);
  };
  const elegirExterno = () => {
    onChange({ id_user: "", name: limpio.slice(0, 120) });
    setTexto(""); setAbierto(false);
  };
  const quitar = () => { onChange({ id_user: "", name: "" }); setTexto(""); };

  const hayValor = Boolean(seleccionada || valor?.name);

  return (
    <div className="persona-combobox" ref={raiz}>
      {hayValor ? (
        <span className="persona-elegida">
          <strong>{seleccionada ? nombreDe(seleccionada) : valor.name}</strong>
          {!seleccionada && <em className="muted"> ({etiquetaExterno})</em>}
          {seleccionada && Number(seleccionada.id_user) === Number(idYo) && (
            <em className="muted"> {etiquetaYo}</em>
          )}
          <button type="button" className="button button-quiet" onClick={quitar}
                  aria-label={vacio}>×</button>
        </span>
      ) : (
        <>
          <input
            id={id}
            type="text"
            role="combobox"
            aria-expanded={abierto}
            autoComplete="off"
            value={texto}
            placeholder={vacio}
            onFocus={() => setAbierto(true)}
            onChange={(e) => { setTexto(e.target.value); setAbierto(true); }}
          />
          {abierto && (coincidencias.length > 0 || ofreceExterno) && (
            <ul className="persona-opciones" role="listbox">
              {coincidencias.map((u) => (
                <li key={u.id_user}>
                  <button type="button" role="option" onClick={() => elegirUsuario(u)}>
                    {nombreDe(u)}
                    {Number(u.id_user) === Number(idYo) ? ` ${etiquetaYo}` : ""}
                  </button>
                </li>
              ))}
              {ofreceExterno && (
                <li className="persona-externo">
                  <button type="button" role="option" onClick={elegirExterno}>
                    {etiquetaExterno}: «{limpio}»
                  </button>
                </li>
              )}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

PersonaCombobox.propTypes = {
  usuarios: PropTypes.arrayOf(PropTypes.object).isRequired,
  valor: PropTypes.shape({ id_user: PropTypes.string, name: PropTypes.string }),
  onChange: PropTypes.func.isRequired,
  vacio: PropTypes.string,
  etiquetaExterno: PropTypes.string,
  etiquetaYo: PropTypes.string,
  idYo: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  id: PropTypes.string,
};
PersonaCombobox.defaultProps = {
  valor: { id_user: "", name: "" },
  vacio: "Escribe un nombre…",
  etiquetaExterno: "Persona externa",
  etiquetaYo: "(tú)",
  idYo: null,
  id: undefined,
};
