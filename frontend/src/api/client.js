const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

/**
 * La URL con la que el navegador pide un archivo servido por el backend.
 *
 * `product.path_imagen` se guarda como ruta relativa -`uploads/products/x.jpg`-
 * y el backend la sirve en esa misma ruta. Pintarla tal cual funcionaba solo
 * cuando el front y el backend comparten origen; con el backend en otro puerto
 * -que es el caso en desarrollo- la imagen salia rota.
 */
export function urlDeArchivo(rutaRelativa) {
  const ruta = String(rutaRelativa || "").trim();
  if (!ruta) return "";
  if (/^https?:\/\//.test(ruta) || ruta.startsWith("data:")) return ruta;
  const limpia = ruta.startsWith("/") ? ruta.slice(1) : ruta;
  // La carpeta del sistema anterior venia en SINGULAR -- `uploads/producto/225.png`
  // -- y la aplicacion sirve `uploads/products/`. Son 2 221 productos migrados
  // con la ruta vieja, asi que sin esto ninguna foto importada carga en ninguna
  // pantalla. Se corrige aqui, en el unico sitio que arma estas URLs, en vez de
  // en cada componente.
  //
  // Es una traduccion de lectura, no un arreglo del dato: `fix_adser_product_image_paths.py`
  // sigue siendo lo que endereza `path_imagen` en la base. Esto hace que la foto
  // se vea aunque ese script no se haya corrido todavia.
  const servible = limpia.replace(/^uploads\/producto\//, "uploads/products/");
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
  return `${base}/${servible}`;
}

function buildUrl(path, params = {}) {
  const isAbsolute = API_BASE_URL.startsWith("http://") || API_BASE_URL.startsWith("https://");
  let urlStr;
  if (isAbsolute) {
    const url = new URL(path, API_BASE_URL);
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
    });
    return url.toString();
  } else {
    const base = API_BASE_URL.endsWith("/") ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const normalizedPath = path.startsWith("/") ? path : "/" + path;
    urlStr = base + normalizedPath;
    const queryParts = Object.entries(params || {})
      .filter(([, v]) => v !== undefined && v !== null && v !== "")
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
    if (queryParts.length) urlStr += "?" + queryParts.join("&");
    return urlStr;
  }
}

export async function request(path, options = {}) {
  const token = options.skipAuth ? null : localStorage.getItem("token");
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };
  const response = await fetch(buildUrl(path, options.params), {
    method: options.method || "GET",
    headers,
    body: options.body ? (isFormData ? options.body : JSON.stringify(options.body)) : undefined
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && !options.skipAuth) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
      return;
    }
    const error = new Error(data.message_key || data.error_key || data.message || "errors.request_failed");
    error.status = response.status;
    error.payload = data;
    throw error;
  }
  return data;
}

export async function requestBlob(path, options = {}) {
  const token = localStorage.getItem("token");
  const response = await fetch(buildUrl(path, options.params), {
    method: options.method || "GET",
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers || {}) }
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = new Error(data.message_key || data.error_key || data.message || "errors.request_failed");
    error.status = response.status;
    error.payload = data;
    throw error;
  }
  return response.blob();
}
