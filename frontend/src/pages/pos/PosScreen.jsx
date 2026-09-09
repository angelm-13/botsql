import React, { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { useI18n } from "../../i18n";
import { posLinks, posRequest, posStatus } from "../../api";
import "../../styles/pos-screens.css";
import PageHeader from "../../components/PageHeader.jsx";

/**
 * Base comun de las pantallas del punto de venta.
 *
 * Todas comparten la misma forma: comprobar que el puente responda, pedir uno o
 * varios recursos al POS y pintar el resultado. Escribir eso cinco veces
 * garantiza que la quinta se olvide de algun caso -el puente sin configurar, la
 * respuesta vacia, el error del POS- y que cada pantalla falle distinto.
 *
 * Lo que resuelve por todas:
 *
 * * el aviso cuando el puente no esta configurado o el POS no responde, con la
 *   causa concreta en vez de una pantalla en blanco;
 * * el mensaje del POS tal cual, que describe el problema mejor que cualquier
 *   texto generico del puente;
 * * el bucle de renders: `t` cambia de identidad en cada render, asi que si
 *   entra en las dependencias del efecto la pantalla se repide sin parar hasta
 *   que el navegador rechaza peticiones. Se guarda en una referencia.
 */

export const listaDe = (respuesta) => {
  if (Array.isArray(respuesta)) return respuesta;
  if (Array.isArray(respuesta?.items)) return respuesta.items;
  if (Array.isArray(respuesta?.results)) return respuesta.results;
  return [];
};

/**
 * El texto legible de un error de la API.
 *
 * El nucleo responde `{error_key: "errors.permission_denied"}` y el cliente lo
 * guarda como `error.message`; el POS responde `{error: "texto en español"}`.
 * Sin distinguirlos, la pantalla acaba enseñando la clave cruda -se midio:
 * salia literalmente "errors.permission_denied" en la caja-, que no le dice
 * nada a quien la lee y ni siquiera esta traducida.
 */
export const mensajeDeError = (error, t) => {
  const delPos = error?.payload?.error;
  if (delPos) return delPos;
  const clave = error?.payload?.error_key || error?.payload?.message_key || error?.message;
  if (!clave) return t("errors.request_failed", "No se pudo completar la operación.");
  // Una clave sin traduccion vuelve tal cual: mas vale un texto tecnico que un
  // hueco, pero se prefiere el traducido cuando existe.
  const texto = t(clave);
  return texto === clave ? t("errors.request_failed", "No se pudo completar la operación.") : texto;
};

export const dinero = (valor) => {
  const numero = Number(valor);
  return Number.isFinite(numero)
    ? numero.toLocaleString("es-MX", { style: "currency", currency: "MXN" })
    : "—";
};

export const numero = (valor) => {
  const n = Number(valor);
  return Number.isFinite(n) ? n.toLocaleString("es-MX") : "—";
};

/**
 * @param {object} props
 * @param {string} props.titulo
 * @param {string} [props.descripcion]
 * @param {Record<string,string>} props.recursos  nombre -> ruta del POS
 * @param {(datos, ayudas) => React.ReactNode} props.children
 */
export default function PosScreen({ titulo, descripcion, recursos, children, acciones }) {
  const { t } = useI18n();
  const [puente, setPuente] = useState(null);
  const [datos, setDatos] = useState({});
  const [cargando, setCargando] = useState(true);
  const [errorTexto, setErrorTexto] = useState("");

  const traducir = useRef(t);
  traducir.current = t;
  // Las rutas se pasan como objeto literal, que cambia de identidad en cada
  // render. Se congela en una referencia para que el efecto no se re-dispare.
  const rutas = useRef(recursos);

  const reportar = useCallback((error) => {
    setErrorTexto(mensajeDeError(error, traducir.current));
  }, []);

  const cargar = useCallback(async () => {
    setCargando(true);
    setErrorTexto("");
    try {
      const estado = await posStatus();
      setPuente(estado);
      if (!estado.configured || !estado.reachable) return;

      const nombres = Object.keys(rutas.current);
      const respuestas = await Promise.all(
        nombres.map((nombre) => {
          const ruta = rutas.current[nombre];
          // `links` no vive en el POS sino en el nucleo: es la
          // correspondencia entre los dos catalogos.
          const peticion = ruta === "@links" ? posLinks() : posRequest(ruta);
          return peticion.catch((error) => {
            // Un recurso que falla no tumba la pantalla entera: las demas
            // secciones siguen siendo utiles, y el fallo se ve en su sitio.
            reportar(error);
            return null;
          });
        })
      );
      setDatos(Object.fromEntries(nombres.map((n, i) => [n, respuestas[i]])));
    } catch (error) {
      reportar(error);
    } finally {
      setCargando(false);
    }
  }, [reportar]);

  useEffect(() => { cargar(); }, [cargar]);

  if (puente && (!puente.configured || !puente.reachable)) {
    return (
      <section className="page pos-screen">
        <h1>{titulo}</h1>
        <div className="pos-blocked">
          <AlertTriangle size={20} />
          <div>
            <p><strong>
              {puente.configured
                ? t("pos.unreachable", "El punto de venta no responde.")
                : t("pos.not_configured", "El puente con el punto de venta no está configurado.")}
            </strong></p>
            <p className="muted">
              {puente.detail || t("pos.bridge_hint",
                "Hacen falta POS_API_URL, POS_SERVICE_USER y POS_SERVICE_PASSWORD en la configuración del servidor.")}
            </p>
            <button className="button" onClick={cargar}>
              <RefreshCw size={15} />{t("common.refresh", "Reintentar")}
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="page pos-screen">
      <PageHeader
        eyebrow={t("pos.eyebrow", "Punto de venta")}
        titulo={titulo}
        subtitulo={descripcion}
      >
        <div className="pos-header-actions">
        {acciones}
        <button className="button" onClick={cargar} disabled={cargando}>
        <RefreshCw size={16} />
        {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
        </div>
      </PageHeader>

      {errorTexto && <p className="error">{errorTexto}</p>}

      {cargando && !Object.keys(datos).length
        ? <p className="muted">{t("common.loading", "Cargando…")}</p>
        : children(datos, { recargar: cargar, cargando, t })}
    </section>
  );
}
