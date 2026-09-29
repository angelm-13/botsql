import { Component } from "react";
import PropTypes from "prop-types";

/**
 * Red de seguridad de toda la aplicacion (ver main.jsx).
 *
 * Por que existe: un error al RENDERIZAR cualquier componente -una variable
 * usada antes de declararse, un dato con una forma que no se esperaba- hace
 * que React desmonte el arbol completo. Sin un limite de error el resultado
 * es una pantalla con solo el color de fondo: sin menu, sin login y sin una
 * sola pista de que paso. Con esto se ve el mensaje y el stack.
 *
 * Clase, no hook: React todavia no tiene un hook equivalente a
 * `getDerivedStateFromError`/`componentDidCatch`.
 *
 * A proposito NO usa i18n, el CSS de la app ni iconos: el fallo que hay que
 * poder mostrar puede venir justo de alguno de ellos, y la pantalla de error
 * no debe depender de lo que acaba de fallar. De ahi los estilos en linea y
 * el texto fijo en español.
 *
 * Solo atrapa errores de render (y de ciclo de vida). Un error dentro de un
 * manejador de eventos o de una promesa no llega aqui: ese no desmonta nada.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null };
    this.recargar = this.recargar.bind(this);
    this.cerrarSesion = this.cerrarSesion.bind(this);
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    this.setState({ info });
    // eslint-disable-next-line no-console
    console.error("La aplicacion no pudo renderizar:", error, info?.componentStack);
  }

  recargar() {
    window.location.reload();
  }

  // Una sesion guardada en mal estado (un usuario con forma inesperada, por
  // ejemplo) puede repetir el mismo error en cada carga; salir de ella es la
  // salida que no obliga a abrir las herramientas del navegador.
  cerrarSesion() {
    try {
      ["token", "user", "mfa_temp_token"].forEach((clave) => localStorage.removeItem(clave));
    } catch (_) { /* sin almacenamiento: nada que limpiar */ }
    window.location.href = "/login";
  }

  render() {
    const { error, info } = this.state;
    if (!error) return this.props.children;
    const boton = {
      font: "inherit", fontWeight: 700, padding: "9px 16px", borderRadius: 10, cursor: "pointer",
      border: "1px solid #c62828", background: "#fff", color: "#c62828",
    };
    return (
      <div role="alert" style={{ maxWidth: 900, margin: "32px auto", padding: "0 16px", fontFamily: "system-ui, sans-serif" }}>
        <div style={{ padding: 20, borderRadius: 14, border: "1px solid #e34948", background: "#fff5f5", color: "#7f1d1d" }}>
          <h1 style={{ margin: "0 0 8px", fontSize: 20, color: "#c62828" }}>La aplicación no pudo mostrarse</h1>
          <p style={{ margin: "0 0 12px" }}>
            Ocurrió un error al dibujar la pantalla. Esto es lo que reportó el navegador:
          </p>
          <p style={{ margin: "0 0 12px", padding: 12, borderRadius: 8, background: "#fff", fontFamily: "monospace", fontWeight: 700, wordBreak: "break-word" }}>
            {String(error?.message || error)}
          </p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", margin: "0 0 14px" }}>
            <button type="button" style={{ ...boton, background: "#c62828", color: "#fff" }} onClick={this.recargar}>Recargar</button>
            <button type="button" style={boton} onClick={this.cerrarSesion}>Cerrar sesión y volver al login</button>
          </div>
          <details>
            <summary style={{ cursor: "pointer", fontWeight: 700 }}>Detalle técnico</summary>
            <pre style={{ whiteSpace: "pre-wrap", fontSize: 11, margin: "8px 0 0", overflow: "auto" }}>
              {[error?.stack, info?.componentStack].filter(Boolean).join("\n")}
            </pre>
          </details>
        </div>
      </div>
    );
  }
}

ErrorBoundary.propTypes = { children: PropTypes.node };
ErrorBoundary.defaultProps = { children: null };
