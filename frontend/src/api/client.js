const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

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
