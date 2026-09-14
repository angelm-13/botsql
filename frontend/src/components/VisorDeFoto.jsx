import { useEffect } from "react";
import PropTypes from "prop-types";
import { X } from "lucide-react";
import { useI18n } from "../i18n";
import "../styles/visor-foto.css";

/**
 * La foto de un producto, en grande.
 *
 * Por qué existe
 * --------------
 * En la lista, la foto va pequeña a propósito: una miniatura grande descuadra
 * el renglón y obliga a desplazarse para leer lo demás. Pero una miniatura de
 * 40px no sirve para lo único que se le pide a la foto de una herramienta —
 * reconocerla — así que hacía falta poder verla entera sin salir de la
 * pantalla.
 *
 * Se abre sobre la página y no en una pestaña nueva: quien compara una foto
 * contra un renglón quiere volver de inmediato, y una pestaña le hace perder el
 * sitio en una lista de doscientos renglones.
 *
 * Se cierra con Escape, con el botón y tocando fuera — las tres, porque cada
 * quien intenta una distinta primero.
 */
export default function VisorDeFoto({ src, titulo, descripcion, onCerrar }) {
  const { t } = useI18n();

  useEffect(() => {
    const alTeclear = (evento) => { if (evento.key === "Escape") onCerrar(); };
    document.addEventListener("keydown", alTeclear);
    // Sin esto la página de atrás sigue desplazándose bajo el visor, que se lee
    // como si el visor se estuviera moviendo.
    const desbordeAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", alTeclear);
      document.body.style.overflow = desbordeAnterior;
    };
  }, [onCerrar]);

  if (!src) return null;

  return (
    <div
      className="visor-foto"
      role="dialog"
      aria-modal="true"
      aria-label={titulo || t("photo.viewer", "Foto del producto")}
      onClick={onCerrar}
    >
      <button
        type="button"
        className="visor-foto-cerrar"
        onClick={onCerrar}
        aria-label={t("common.close", "Cerrar")}
      >
        <X size={20} />
      </button>

      {/* El clic en la imagen no cierra: quien la está mirando no quiere que
          se le escape por tocarla. */}
      <figure className="visor-foto-marco" onClick={(e) => e.stopPropagation()}>
        <img src={src} alt={titulo || ""} />
        {(titulo || descripcion) && (
          <figcaption>
            {titulo && <strong>{titulo}</strong>}
            {descripcion && <span>{descripcion}</span>}
          </figcaption>
        )}
      </figure>
    </div>
  );
}

VisorDeFoto.propTypes = {
  src: PropTypes.string,
  titulo: PropTypes.string,
  descripcion: PropTypes.string,
  onCerrar: PropTypes.func.isRequired,
};
VisorDeFoto.defaultProps = { src: "", titulo: "", descripcion: "" };
