// Como se nombra a una persona en los filtros del dashboard, y cuando hace falta un texto secundario para distinguirla.
// Puro y sin React -- ver kpiPersonas.test.js.
import { normalizarBusqueda } from "./kpiDatos.js";

/** El nombre completo; sin el, el usuario; sin ninguno, "#id". */
export function nombreDePersona(usuario) {
  return usuario?.full_name || usuario?.username || `#${usuario?.id_user}`;
}

/** El texto secundario de cada persona que se confunde con otra: `Map(String(id_user) -> texto)`. Solo salen las
 * que hace falta distinguir.
 *
 * - Se confunden dos personas con el mismo nombre (sin distinguir mayusculas ni acentos) o cuando el nombre de una es
 *   el principio del de otra ("Juan Perez" y "Juan Perez Lopez": un nombre cortado en otra pantalla).
 * - El texto es el rol (`role`, de /user/options). Si el rol tampoco las distingue (mismo nombre y mismo rol), se le
 *   agrega el usuario o, en ultimo caso, el id: nunca quedan dos chips identicos.
 * - Quien no se confunde con nadie no lleva texto. */
export function detallesDePersonas(usuarios) {
  const lista = Array.isArray(usuarios) ? usuarios : [];
  const normales = lista.map((usuario) => normalizarBusqueda(nombreDePersona(usuario)));
  const confundidas = lista.filter((_, i) => normales.some((otro, j) => j !== i
    && (otro === normales[i] || otro.startsWith(`${normales[i]} `) || normales[i].startsWith(`${otro} `))));
  const detalles = new Map();
  const base = (usuario) => String(usuario.role || "").trim();
  confundidas.forEach((usuario) => {
    const igualesAlRol = confundidas.filter((otro) => otro !== usuario && base(otro) === base(usuario));
    let texto = base(usuario);
    if (!texto || igualesAlRol.length) {
      const usuarioTexto = usuario.username ? `@${usuario.username}` : `#${usuario.id_user}`;
      const colisionaUsuario = igualesAlRol.some((otro) => (otro.username ? `@${otro.username}` : `#${otro.id_user}`) === usuarioTexto);
      const ultimoRecurso = colisionaUsuario ? `#${usuario.id_user}` : usuarioTexto;
      texto = texto ? `${texto} · ${ultimoRecurso}` : ultimoRecurso;
    }
    detalles.set(String(usuario.id_user), texto);
  });
  return detalles;
}
