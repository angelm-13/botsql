// Como se nombra en pantalla lo que la nomina guarda como numero: un periodo,
// un empleado, un detalle (empleado en un periodo) o un concepto.
//
// Las pantallas de Detalle y Movimientos mostraban los ids crudos (id_user,
// id_payroll_period, id_payroll_detail...). Una sola regla aqui para las dos;
// si no se encuentra el registro, se muestra el numero tal cual.

const porId = (lista, campo) => new Map((Array.isArray(lista) ? lista : []).map((x) => [String(x?.[campo]), x]));

export function etiquetaPeriodo(periodo) {
  if (!periodo) return "";
  const fechas = periodo.period_start && periodo.period_end ? ` · ${periodo.period_start} al ${periodo.period_end}` : "";
  return `#${periodo.id_payroll_period}${fechas}`;
}

export function etiquetaUsuario(usuario) {
  if (!usuario) return "";
  return usuario.full_name || usuario.username || `#${usuario.id_user}`;
}

export function etiquetaConcepto(concepto) {
  if (!concepto) return "";
  const codigo = concepto.payroll_code ? ` (${concepto.payroll_code})` : "";
  return `${concepto.payroll_concept_description || ""}${codigo}` || `#${concepto.id_payroll_concept}`;
}

// Arma las funciones `(id) => texto` a partir de las listas que cargo la pantalla.
export function crearEtiquetas({ periodos = [], usuarios = [], detalles = [], conceptos = [] } = {}) {
  const P = porId(periodos, "id_payroll_period");
  const U = porId(usuarios, "id_user");
  const D = porId(detalles, "id_payroll_detail");
  const C = porId(conceptos, "id_payroll_concept");
  const crudo = (id) => (id === null || id === undefined || id === "" ? "" : String(id));

  const periodo = (id) => (P.has(String(id)) ? etiquetaPeriodo(P.get(String(id))) : crudo(id));
  const usuario = (id) => (U.has(String(id)) ? etiquetaUsuario(U.get(String(id))) : crudo(id));
  const concepto = (id) => (C.has(String(id)) ? etiquetaConcepto(C.get(String(id))) : crudo(id));
  const detalle = (id) => {
    const d = D.get(String(id));
    if (!d) return crudo(id);
    return `${usuario(d.id_user)} · ${periodo(d.id_payroll_period)}`;
  };
  return { periodo, usuario, concepto, detalle };
}
