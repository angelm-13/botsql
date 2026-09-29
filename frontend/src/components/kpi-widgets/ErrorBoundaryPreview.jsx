import { Component } from "react";
import PropTypes from "prop-types";
import { AlertTriangle } from "lucide-react";

/**
 * Solo para /dashboard-preview -- no envuelve el resto de la app. Un error
 * de render aqui (un import que no existe, un componente undefined, un
 * acceso a un dato demo que cambio de forma) dejaba la pantalla en blanco
 * sin ningun rastro visible; con esto al menos se ve el mensaje y el stack
 * en la propia pagina, en vez de nada.
 *
 * Clase, no hook: React todavia no tiene un hook equivalente a
 * `getDerivedStateFromError`/`componentDidCatch` -- un error boundary tiene
 * que ser una clase.
 */
export default class ErrorBoundaryPreview extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("Error en /dashboard-preview:", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div style={{
        margin: 24, padding: 20, borderRadius: 12, border: "1px solid #e34948",
        background: "#fff5f5", color: "#c62828", fontFamily: "monospace",
      }}
      >
        <p style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 800, margin: "0 0 10px" }}>
          <AlertTriangle size={18} aria-hidden="true" />
          /dashboard-preview no pudo renderizar
        </p>
        <p style={{ margin: "0 0 8px" }}>{String(error?.message || error)}</p>
        {error?.stack && (
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 11, opacity: .8, margin: 0 }}>{error.stack}</pre>
        )}
      </div>
    );
  }
}

ErrorBoundaryPreview.propTypes = { children: PropTypes.node };
ErrorBoundaryPreview.defaultProps = { children: null };
