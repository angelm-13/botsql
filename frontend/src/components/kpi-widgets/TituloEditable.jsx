import { useRef, useState } from "react";
import PropTypes from "prop-types";
import { Pencil } from "lucide-react";
import { TITULO_MAX, contadorDeTitulo, tituloEditado } from "../../kpi/kpiParametros.js";

// El titulo del grafico dentro de la vista previa, como campo editable: clic en el rectangulo o en el lapiz edita en el
// lugar; Enter guarda, Esc cancela. Vacio vuelve al titulo por defecto (el nombre del KPI).
export default function TituloEditable({ valor, porDefecto, onGuardar, etiqueta, editar }) {
  const [borrador, setBorrador] = useState(null);
  const cancelado = useRef(false);
  const editando = borrador !== null;

  function guardar() {
    if (!editando) return;
    onGuardar(tituloEditado(borrador));
    setBorrador(null);
  }

  function alTeclear(evento) {
    if (evento.key === "Enter") { evento.preventDefault(); guardar(); }
    else if (evento.key === "Escape") { evento.preventDefault(); cancelado.current = true; setBorrador(null); }
  }

  function alSalir() {
    // Esc ya cerro la edicion: el blur que llega despues no debe guardar lo descartado.
    if (cancelado.current) { cancelado.current = false; return; }
    guardar();
  }

  const contador = editando ? contadorDeTitulo(borrador) : null;

  return (
    <>
      <div className="kpi-titulo-editable" onClick={() => { if (!editando) setBorrador(valor); }}>
        {editando ? (
          <input
            type="text"
            autoFocus
            value={borrador}
            maxLength={TITULO_MAX}
            placeholder={porDefecto}
            aria-label={etiqueta}
            onChange={(evento) => setBorrador(evento.target.value)}
            onKeyDown={alTeclear}
            onBlur={alSalir}
          />
        ) : (
          <strong>{tituloEditado(valor) || porDefecto}</strong>
        )}
        <button type="button" className="kpi-icon-button" title={editar} aria-label={editar} onMouseDown={(e) => e.preventDefault()} onClick={(e) => { e.stopPropagation(); if (!editando) setBorrador(valor); }}>
          <Pencil size={15} />
        </button>
      </div>
      {contador && <p className="kpi-titulo-contador">{contador.usados}/{contador.max}</p>}
    </>
  );
}

TituloEditable.propTypes = {
  valor: PropTypes.string,
  porDefecto: PropTypes.string,
  onGuardar: PropTypes.func.isRequired,
  etiqueta: PropTypes.string,
  editar: PropTypes.string,
};
