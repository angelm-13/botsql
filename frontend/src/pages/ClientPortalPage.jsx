import { useEffect, useState } from "react";
import { Check, LogOut, MessageSquare, X } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5001";
const TOKEN_KEY = "tyakxa_client_portal_token";

async function request(path, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error_key || "No se pudo completar la solicitud");
  return payload;
}

export default function ClientPortalPage() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [credentials, setCredentials] = useState({ email: "", password: "" });
  const [quotations, setQuotations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try { setQuotations((await request("/public/client-portal/quotations")).items || []); }
    catch (err) { setError(err.message); }
  }

  useEffect(() => { if (token) load(); }, [token]);

  async function login(event) {
    event.preventDefault(); setError("");
    try {
      const payload = await request("/public/auth/login", { method: "POST", body: JSON.stringify(credentials) });
      localStorage.setItem(TOKEN_KEY, payload.token); setToken(payload.token);
    } catch (err) { setError(err.message); }
  }

  async function openQuotation(id) { setSelected(await request(`/public/client-portal/quotations/${id}`)); }
  async function decide(decision) { await request(`/public/client-portal/quotations/${selected.quotation.id_invoice}/decision`, { method: "POST", body: JSON.stringify({ decision }) }); await openQuotation(selected.quotation.id_invoice); await load(); }
  async function sendComment(event) { event.preventDefault(); await request(`/public/client-portal/quotations/${selected.quotation.id_invoice}/comments`, { method: "POST", body: JSON.stringify({ message: comment }) }); setComment(""); await openQuotation(selected.quotation.id_invoice); }

  if (!token) return <main className="auth-page"><form className="auth-card" onSubmit={login}><h1>Portal de cliente</h1><label>Correo<input required type="email" value={credentials.email} onChange={(event) => setCredentials({ ...credentials, email: event.target.value })} /></label><label>Contraseña<input required type="password" value={credentials.password} onChange={(event) => setCredentials({ ...credentials, password: event.target.value })} /></label>{error && <p className="error">{error}</p>}<button type="submit">Ingresar</button></form></main>;

  return <main className="page"><header className="page-header"><div><p className="eyebrow">Portal de cliente</p><h1>Mis cotizaciones</h1></div><button title="Cerrar sesión" onClick={() => { localStorage.removeItem(TOKEN_KEY); setToken(null); }}><LogOut size={18} /></button></header>{error && <p className="error">{error}</p>}<div className="table-wrap"><table><thead><tr><th>Folio</th><th>Fecha</th><th>Estado</th><th>Total</th></tr></thead><tbody>{quotations.map((row) => <tr key={row.id_invoice} onClick={() => openQuotation(row.id_invoice)}><td>{row.folio || `COT-${row.id_invoice}`}</td><td>{row.date_emision?.slice(0, 10) || "—"}</td><td>{row.invoice_status}</td><td>{row.total} {row.currency}</td></tr>)}</tbody></table></div>{selected && <section className="quotation-detail"><h2>{selected.quotation.folio || `COT-${selected.quotation.id_invoice}`}</h2><div className="actions"><button onClick={() => decide("accept")}><Check size={17} /> Aceptar</button><button onClick={() => decide("reject")}><X size={17} /> Rechazar</button></div><h3>Partidas</h3>{selected.lines.map((line) => <p key={line.id_invoice_material_service}>{line.invoice_material_service_description} · {line.quantity}</p>)}<h3><MessageSquare size={17} /> Comentarios</h3>{selected.comments.map((item) => <p key={item.id_quotation_comment}>{item.message}</p>)}<form onSubmit={sendComment}><label className="field"><span>Comentario</span><textarea required value={comment} onChange={(event) => setComment(event.target.value)} maxLength={1000} /></label><button type="submit">Enviar comentario</button></form></section>}</main>;
}