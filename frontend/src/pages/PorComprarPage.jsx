import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { getMaterialNeedsToBuy } from "../api";
import { useI18n } from "../i18n";
import "../styles/material-necesario.css";

function fechaCorta(iso) {
  if (!iso) return "";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("es-MX");
}

function etiquetaDeProyecto(p) {
  const folio = p.folio ? `#${p.folio}` : `#${p.id_proyect}`;
  return p.title ? `${folio} — ${p.title}` : folio;
}

/**
 * Lo que hace falta comprar: las necesidades de TODOS los proyectos, agrupadas
 * por material y contra la existencia del almacen.
 *
 * Un mismo material pedido por tres proyectos es UNA compra: eso es lo que esta
 * vista deja ver y la de cada proyecto no. "Hay" es la existencia de hoy y
 * "Falta" es lo pedido en total menos eso; no se reserva nada para ningun
 * proyecto en particular.
 */
export default function PorComprarPage() {
  const { t } = useI18n();
  // `t` cambia en cada render; como dependencia de `cargar` lo repetia sin parar.
  const traducir = useRef(t);
  traducir.current = t;
  const [respuesta, setRespuesta] = useState(null);
  const [soloFaltantes, setSoloFaltantes] = useState(true);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      setRespuesta(await getMaterialNeedsToBuy({ only_missing: soloFaltantes ? 1 : 0 }));
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key, "No se pudo cargar la lista.")
        : traducir.current("errors.request_failed", "No se pudo cargar la lista."));
    } finally {
      setCargando(false);
    }
  }, [soloFaltantes]);

  useEffect(() => { cargar(); }, [cargar]);

  const items = respuesta?.items || [];

  return (
    <section className="page por-comprar">
      <PageHeader
        eyebrow={t("purchase.eyebrow", "Compras")}
        titulo={t("purchase.title", "Por comprar")}
        subtitulo={t("purchase.subtitle",
          "Lo que piden los proyectos contra lo que hay en el almacén. Un material que piden varios proyectos es una sola compra.")}
      >
        <button type="button" className="button ghost" onClick={cargar} disabled={cargando}>
          <RefreshCw size={16} />
          {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
      </PageHeader>

      <label className="por-comprar-filtro">
        <input type="checkbox" checked={!soloFaltantes}
               onChange={(e) => setSoloFaltantes(!e.target.checked)} />
        {t("purchase.show_covered", "Ver también lo que ya cubre el almacén")}
      </label>

      {error && <div className="alert error">{error}</div>}

      {!cargando && !error && items.length === 0 && (
        <div className="empty">
          <strong>{soloFaltantes
            ? t("purchase.nothing_missing", "No falta nada por comprar.")
            : t("purchase.nothing_asked", "Ningún proyecto ha pedido material.")}</strong>
        </div>
      )}

      {items.length > 0 && (
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>{t("purchase.col_material", "Material")}</th>
                <th>{t("purchase.col_required", "Piden")}</th>
                <th>{t("purchase.col_stock", "Hay")}</th>
                <th>{t("purchase.col_missing", "Falta")}</th>
                <th>{t("purchase.col_needed_by", "Para cuándo")}</th>
                <th>{t("purchase.col_projects", "Proyectos")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((g) => (
                <tr key={g.material?.id_material}>
                  <td>
                    <strong>{g.material?.material_description}</strong>
                    {g.material?.unit && <span className="muted"> · {g.material.unit}</span>}
                  </td>
                  <td className="mono">{g.required}</td>
                  <td className="mono">{g.in_stock}</td>
                  <td className={`mono ${g.missing > 0 ? "por-comprar-falta" : "por-comprar-cubierto"}`}>
                    {g.missing > 0 ? g.missing : t("purchase.covered", "cubierto")}
                  </td>
                  <td>{fechaCorta(g.needed_by) || <span className="muted">—</span>}</td>
                  <td>
                    <ul className="por-comprar-proyectos">
                      {g.projects.map((p) => (
                        <li key={p.id_proyect_material_need}>
                          <span>{etiquetaDeProyecto(p)}</span>
                          <span className="mono">{p.quantity}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
