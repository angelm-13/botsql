/* eslint-disable react/prop-types, react-refresh/only-export-components */
// Se empaqueta para el NAVEGADOR (ver navegadorSelector.test.mjs): monta el
// SelectorDeKpi con estado real -la seleccion vive aqui, como en el editor- para
// que un Chrome de verdad pueda hacer clic, escribir y medir.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { ClipboardList, Boxes, FileText, FlaskConical, Receipt } from "lucide-react";
import SelectorDeKpi from "../components/kpi-widgets/SelectorDeKpi.jsx";

const META = {
  facturacion: { icon: Receipt, label: "Facturación" },
  operaciones: { icon: ClipboardList, label: "Operaciones" },
  inventario: { icon: Boxes, label: "Inventario" },
  laboratorio: { icon: FlaskConical, label: "Laboratorio" },
  documentos: { icon: FileText, label: "Documentos" },
};

function Envoltura({ catalogo, seleccionadosIniciales, multiple }) {
  const [seleccionados, setSeleccionados] = useState(seleccionadosIniciales);
  const [colores, setColores] = useState({});
  return (
    <SelectorDeKpi
      catalogo={catalogo}
      seleccionados={seleccionados}
      multiple={multiple}
      onAlternar={(id) => setSeleccionados((actual) => (
        actual.includes(id) ? actual.filter((otro) => otro !== id) : (multiple ? [...actual, id] : [id])
      ))}
      metaDeModulo={(modulo) => META[modulo] || { icon: Boxes, label: modulo }}
      textoDeBloqueo={(kpi, motivo) => `No se puede combinar (${motivo}): ${kpi.etiqueta}`}
      coloresKpi={colores}
      onElegirColor={(id, color) => setColores((actual) => ({ ...actual, [id]: color }))}
    />
  );
}

window.montarSelector = ({ contenedor, catalogo, seleccionados = [], multiple = false }) => {
  createRoot(contenedor).render(<Envoltura catalogo={catalogo} seleccionadosIniciales={seleccionados} multiple={multiple} />);
};
