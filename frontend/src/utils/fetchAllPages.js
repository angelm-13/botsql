// Trae TODAS las paginas de un listado, no solo la primera.
//
// Por que existe
// ---------------
// Las pantallas genericas calculan que ve el rol pidiendo `entity_permission`,
// `field` y `nm_field_permission` completos con un `per_page` fijo (5000) de
// una sola vez. Mientras las tres tablas cupieran ahi, funcionaba. Pero
// `nm_field_permission` crece con roles x modulos x campos, y ya paso de esa
// cifra: con 12 roles y casi 100 modulos son miles de filas, y la pagina 2
// nunca se pedia.
//
// El efecto no era "esta pantalla no carga": era mas dificil de notar. Una
// cuenta con `user_type = 'admin'` (que entra por las rutas SIN filtrar del
// backend, no por `/security/my-permissions`, que ya viene filtrado) se
// quedaba sin las filas de permiso de campo que cayeran en la pagina 2, y la
// pantalla generica se veia con menos columnas que otra cuenta con el MISMO
// permiso real -- se investigo como "por que yesgo ve menos que admin1 con el
// mismo rol", y la respuesta era esta cota, no un permiso mal puesto.
//
// Se pagina aqui, en un solo sitio, para que las ~45 pantallas genericas que
// comparten este patron no repitan cada una su propio bucle.
export async function fetchAllPages(fetcher, params = {}) {
  const perPage = 5000;
  let page = 1;
  let items = [];
  for (;;) {
    const payload = await fetcher({ ...params, page, per_page: perPage });
    const batch = Array.isArray(payload) ? payload : (payload?.items || payload?.data || payload?.records || []);
    items = items.concat(batch);
    const pages = Number(payload?.pages ?? 1);
    if (!batch.length || page >= pages) break;
    page += 1;
  }
  return { items };
}
