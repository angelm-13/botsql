import PropTypes from "prop-types";
import {
  ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight,
} from "lucide-react";
import { useI18n } from "../i18n";
import "../styles/pagination.css";

/**
 * La paginación, una sola vez.
 *
 * Qué estaba mal
 * --------------
 * Cuarenta y nueve pantallas repetían esto:
 *
 *     <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
 *     <span>Página {page}</span>
 *     <button onClick={() => setPage(page + 1)}>Siguiente</button>
 *
 * Y tiene tres fallos, los tres visibles en cuanto hay datos de verdad:
 *
 *   * **«Siguiente» nunca se deshabilita.** No mira `pages`, así que en una
 *     lista de tres páginas se puede llegar a la 47 y quedarse mirando una
 *     tabla vacía sin saber que se pasó de largo;
 *   * **no dice cuántas hay.** «Página 5» y nunca «de 56»: no hay forma de
 *     saber si falta una página o cincuenta;
 *   * **no hay salto.** Con 2 221 productos son 56 páginas de a 40, y llegar a
 *     la última son 55 clics.
 *
 * Y el servidor ya devolvía `total`, `page`, `per_page` y `pages` en todas esas
 * respuestas. El front los tiraba a la basura.
 *
 * Qué hace de más
 * ---------------
 * Acota la página al rango: `onChange` nunca recibe algo fuera de [1, pages].
 * Sin eso, dos clics rápidos en «Siguiente» adelantan el contador más allá del
 * final, el servidor devuelve la última página, y los siguientes clics en
 * «Anterior» no hacen nada visible hasta que el contador vuelve al rango.
 */

export default function Pagination({
  page, pages, total, perPage, onChange, loading, etiquetaDeTotal,
  opcionesDeTamano, onTamano,
}) {
  const { t } = useI18n();

  const totalDePaginas = Math.max(1, Number(pages) || 1);
  const actual = Math.min(Math.max(1, Number(page) || 1), totalDePaginas);

  // Acotar aquí y no en cada pantalla: es el fallo que se repetía en las 49.
  const ir = (destino) => {
    const acotado = Math.min(Math.max(1, destino), totalDePaginas);
    if (acotado !== actual) onChange(acotado);
  };

  const desde = total ? (actual - 1) * (Number(perPage) || 0) + 1 : 0;
  const hasta = total
    ? Math.min(actual * (Number(perPage) || 0), Number(total))
    : 0;

  return (
    <nav className="paginacion" aria-label={t("common.pagination", "Paginación")}>
      <div className="paginacion-botones">
        <button
          type="button" className="button"
          onClick={() => ir(1)} disabled={loading || actual <= 1}
          title={t("common.first_page", "Primera")}
          aria-label={t("common.first_page", "Primera página")}
        >
          <ChevronsLeft size={15} />
        </button>
        <button
          type="button" className="button"
          onClick={() => ir(actual - 1)} disabled={loading || actual <= 1}
        >
          <ChevronLeft size={15} />
          {t("common.previous", "Anterior")}
        </button>

        {/* El salto directo. Con 56 páginas, llegar al final a base de clics no
            es navegar. Se aplica al salir del campo o con Enter, no en cada
            tecla: si no, teclear "12" pediría antes la página 1. */}
        <label className="paginacion-salto">
          <span className="muted">{t("common.page", "Página")}</span>
          <input
            type="number" min={1} max={totalDePaginas}
            defaultValue={actual}
            key={actual}
            disabled={loading || totalDePaginas <= 1}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                ir(Number(e.currentTarget.value));
              }
            }}
            onBlur={(e) => ir(Number(e.currentTarget.value))}
            aria-label={t("common.go_to_page", "Ir a la página")}
          />
          <span className="muted">
            {t("common.of", "de")} <strong>{totalDePaginas}</strong>
          </span>
        </label>

        <button
          type="button" className="button"
          onClick={() => ir(actual + 1)}
          disabled={loading || actual >= totalDePaginas}
        >
          {t("common.next", "Siguiente")}
          <ChevronRight size={15} />
        </button>
        <button
          type="button" className="button"
          onClick={() => ir(totalDePaginas)}
          disabled={loading || actual >= totalDePaginas}
          title={t("common.last_page", "Última")}
          aria-label={t("common.last_page", "Última página")}
        >
          <ChevronsRight size={15} />
        </button>
      </div>

      {/* Cuántos registros hay, que es la otra mitad de la pregunta: sin esto,
          «Página 5 de 56» no dice si son doscientos o dos mil. */}
      {Number(total) > 0 && (
        <span className="paginacion-cuenta muted">
          {perPage ? `${desde}–${hasta} ${t("common.of", "de")} ` : ""}
          <strong>{total}</strong>{" "}
          {etiquetaDeTotal || t("common.records", "registros")}
        </span>
      )}

      {/* Cuantos ver de golpe. Va junto a la cuenta porque son la misma
          pregunta: cuantos hay y cuantos quiero mirar a la vez. Solo aparece si
          la pantalla lo pide -no toda lista gana algo con el-. */}
      {onTamano && opcionesDeTamano.length > 0 && (
        <label className="paginacion-tamano">
          <span className="muted">{t("common.show", "Ver")}</span>
          <select
            value={String(Number(perPage) || opcionesDeTamano[0])}
            disabled={loading}
            onChange={(e) => onTamano(Number(e.target.value))}
            aria-label={t("common.per_page", "Cuantos por página")}
          >
            {opcionesDeTamano.map((cuantos) => (
              <option key={cuantos} value={String(cuantos)}>{cuantos}</option>
            ))}
          </select>
        </label>
      )}
    </nav>
  );
}

Pagination.propTypes = {
  page: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  pages: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  total: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  perPage: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  onChange: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  etiquetaDeTotal: PropTypes.string,
  opcionesDeTamano: PropTypes.arrayOf(PropTypes.number),
  onTamano: PropTypes.func,
};

Pagination.defaultProps = {
  page: 1,
  pages: 1,
  total: 0,
  perPage: 0,
  loading: false,
  etiquetaDeTotal: "",
  opcionesDeTamano: [],
  onTamano: null,
};
