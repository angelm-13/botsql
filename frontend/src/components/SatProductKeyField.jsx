import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Check, Loader2, Search } from "lucide-react";
import { searchSatProductKeys } from "../api";
import { useI18n } from "../i18n";

/**
 * Campo de captura de la ClaveProdServ del SAT con busqueda.
 *
 * Sin esto hay que teclear de memoria una clave de ocho digitos de un catalogo
 * de mas de cincuenta mil. Se puede escribir la clave directamente o buscar por
 * texto ("reparacion de pc") y elegir de la lista.
 *
 * El componente no valida la clave: eso lo hace el backend contra el catalogo
 * real. Aqui solo se busca y se elige, para no tener dos fuentes de verdad.
 */
const DEBOUNCE_MS = 300;
const KEY_PATTERN = /^[0-9]{8}$/;

export default function SatProductKeyField({ value, onChange, onDescriptionPick, required, disabled }) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [highlighted, setHighlighted] = useState(0);
  const containerRef = useRef(null);
  // Cada busqueda lleva un numero: si llega una respuesta atrasada mientras el
  // usuario sigue escribiendo, se descarta en lugar de pisar la lista actual.
  const requestRef = useRef(0);

  const isValidKey = useMemo(() => KEY_PATTERN.test(String(value || "")), [value]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const runSearch = useCallback((text) => {
    const term = String(text || "").trim();
    if (term.length < 2) {
      setResults([]);
      setError("");
      return;
    }
    const ticket = requestRef.current + 1;
    requestRef.current = ticket;
    setBusy(true);
    searchSatProductKeys(term)
      .then((payload) => {
        if (requestRef.current !== ticket) return;
        const items = payload?.items || [];
        setResults(items);
        setHighlighted(0);
        setError(
          payload?.catalog_loaded === false
            ? t("sat_catalog.not_loaded", "El catálogo del SAT no está cargado. Pide que se importe para poder buscar.")
            : "",
        );
      })
      .catch(() => {
        if (requestRef.current !== ticket) return;
        setResults([]);
        setError(t("sat_catalog.search_failed", "No se pudo buscar en el catálogo."));
      })
      .finally(() => {
        if (requestRef.current === ticket) setBusy(false);
      });
  }, [t]);

  useEffect(() => {
    if (!open) return undefined;
    const timer = window.setTimeout(() => runSearch(query), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [open, query, runSearch]);

  function pick(item) {
    onChange(item.clave);
    // La descripcion del catalogo solo se propone cuando la partida aun no
    // tiene una: lo que el usuario ya escribio describe mejor su venta.
    onDescriptionPick?.(item.description);
    setOpen(false);
    setQuery("");
  }

  function handleKeyDown(event) {
    if (!open || !results.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlighted((current) => (current + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlighted((current) => (current - 1 + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      pick(results[highlighted]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="sat-key-field" ref={containerRef}>
      <div className="sat-key-input-row">
        <input
          required={required}
          disabled={disabled}
          inputMode="numeric"
          maxLength="8"
          placeholder="81111500"
          value={value || ""}
          onChange={(event) => onChange(event.target.value.replace(/\D/g, "").slice(0, 8))}
          aria-invalid={Boolean(value) && !isValidKey}
        />
        <button
          className="button ghost sat-key-search-button"
          type="button"
          disabled={disabled}
          title={t("sat_catalog.search_title", "Buscar clave en el catálogo del SAT")}
          onClick={() => setOpen((current) => !current)}
        >
          <Search size={15} />
        </button>
      </div>
      {value && !isValidKey && (
        <small className="sat-key-hint error">
          {t("sat_catalog.key_must_be_8_digits", "La clave del SAT tiene 8 dígitos.")}
        </small>
      )}
      {open && (
        <div className="sat-key-popover">
          <div className="sat-key-search">
            {busy ? <Loader2 className="spin" size={15} /> : <Search size={15} />}
            <input
              autoFocus
              placeholder={t("sat_catalog.search_placeholder", "Busca por texto o por clave: reparación de pc, 8111...")}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>
          {error && <p className="sat-key-message error">{error}</p>}
          {!error && query.trim().length < 2 && (
            <p className="sat-key-message">
              {t("sat_catalog.type_to_search", "Escribe al menos dos letras para buscar.")}
            </p>
          )}
          {!error && query.trim().length >= 2 && !busy && !results.length && (
            <p className="sat-key-message">
              {t("sat_catalog.no_results", "Sin resultados. Prueba con otra palabra.")}
            </p>
          )}
          {Boolean(results.length) && (
            <ul className="sat-key-results">
              {results.map((item, index) => (
                <li key={item.clave}>
                  <button
                    type="button"
                    className={index === highlighted ? "highlighted" : ""}
                    onMouseEnter={() => setHighlighted(index)}
                    onClick={() => pick(item)}
                  >
                    <span className="sat-key-code">{item.clave}</span>
                    <span className="sat-key-description">{item.description}</span>
                    {item.clave === value && <Check className="sat-key-check" size={14} />}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

SatProductKeyField.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  onDescriptionPick: PropTypes.func,
  required: PropTypes.bool,
  disabled: PropTypes.bool,
};
