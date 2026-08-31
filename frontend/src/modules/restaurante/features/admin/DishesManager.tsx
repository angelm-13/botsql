import { useCallback, useEffect, useState, type CSSProperties } from 'react';
import { Eye, EyeOff, Plus, Search } from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { useCategories } from '../../contexts/CategoriesContext';
import { CatIcon, ICON_OPTIONS } from '../../components/shared/CatIcon';
import type { Translations } from '../../i18n/translations';
import type { Dish, Guisado, DishSchedule } from '../../types/api';

interface DishForm {
  title: string
  price: string
  size_label: string
  description: string
  image_url: string
  requires_guisado: boolean
  schedule: DishSchedule
}

export function DishesManager({ t }: { t: Translations }) {
  const toast = useToast();
  const { categories, reloadCategories } = useCategories();
  const [category, setCategory] = useState<string | null>(null);
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [guisados, setGuisados] = useState<Guisado[]>([]);
  const [form, setForm] = useState<DishForm>({ title: '', price: '', size_label: '', description: '', image_url: '', requires_guisado: false, schedule: 'all' });
  const [newGuisado, setNewGuisado] = useState('');
  const [newCategory, setNewCategory] = useState({ name: '', icon: 'utensils', color: '#71717a' });
  const [search, setSearch] = useState('');
  const [showInactive, setShowInactive] = useState(false);

  useEffect(() => { if (!category && categories.length) setCategory(categories[0].slug); }, [categories.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async () => {
    if (!category) { setDishes([]); return; }
    const inactiveParam = showInactive ? '&include_inactive=1' : '';
    const [d, g] = await Promise.all([api.dishes(`?category=${category}&per_page=200${inactiveParam}`), api.guisados()]);
    setDishes(d.items || []); setGuisados(g.items || []);
  }, [category, showInactive]);
  useEffect(() => { load().catch(console.error); }, [load]);

  // Todas las mutaciones de aqui abajo llevan try/catch + toast.error: antes
  // ninguna lo tenia, asi que un 422 del backend (precio negativo, nombre de
  // categoria/guisado duplicado, etc.) quedaba como una promesa rechazada
  // sin manejar -- no aparecia ningun aviso, el formulario simplemente no
  // se limpiaba, y el admin no tenia forma de saber que habia pasado.
  async function addDish() {
    if (!form.title) { toast.error(t.missingTitle); return; }
    if (form.price === '' || form.price === null) { toast.error(t.missingPrice); return; }
    try {
      await api.createDish({ ...form, category: category!, price: Number(form.price) });
      setForm({ title: '', price: '', size_label: '', description: '', image_url: '', requires_guisado: false, schedule: 'all' });
      load().catch(console.error);
    } catch (e) { toast.error((e as Error).message); }
  }
  async function updateDish(dish: Dish, field: string, value: unknown) {
    try { await api.updateDish(dish.id, { [field]: value }); load().catch(console.error); }
    catch (e) { toast.error((e as Error).message); }
  }
  async function toggleDishActive(dish: Dish) { await updateDish(dish, 'is_active', !dish.is_active); }
  async function addGuisado() {
    if (!newGuisado) return;
    try { await api.createGuisado(newGuisado); setNewGuisado(''); load().catch(console.error); }
    catch (e) { toast.error((e as Error).message); }
  }
  async function deleteGuisado(id: number) {
    try { await api.deleteGuisado(id); load().catch(console.error); }
    catch (e) { toast.error((e as Error).message); }
  }
  async function addCategory() {
    if (!newCategory.name.trim()) return;
    try {
      await api.createCategory(newCategory);
      setNewCategory({ name: '', icon: 'utensils', color: '#71717a' });
      reloadCategories();
    } catch (e) { toast.error((e as Error).message); }
  }
  async function deleteCategory(id: number) {
    try { await api.deleteCategory(id); reloadCategories(); }
    catch (e) { toast.error((e as Error).message); }
  }

  const term = search.trim().toLowerCase();
  const filteredDishes = term ? dishes.filter(d => d.title.toLowerCase().includes(term)) : dishes;

  return <section>
    <h3>{t.categories}</h3>
    <div className="pill-list">
      {categories.map(c => <span className="pill-tag" style={{ '--pill-color': c.color } as CSSProperties} key={c.id}>
        <CatIcon category={c.slug} size={14} /> {c.name}
        <button className="pill-tag-remove" onClick={() => deleteCategory(c.id)}>&times;</button>
      </span>)}
    </div>
    <div className="inline-form-row">
      <input placeholder={t.categoryName} value={newCategory.name} onChange={e => setNewCategory({ ...newCategory, name: e.target.value })} />
      <select value={newCategory.icon} onChange={e => setNewCategory({ ...newCategory, icon: e.target.value })} title={t.categoryIcon}>
        {Object.keys(ICON_OPTIONS).map(key => <option key={key} value={key}>{key}</option>)}
      </select>
      <input type="color" value={newCategory.color} onChange={e => setNewCategory({ ...newCategory, color: e.target.value })} title={t.categoryColor} />
      <button className="primary" onClick={addCategory}><Plus size={16} /> {t.addCategory}</button>
    </div>

    <div className="category-tabs" style={{ marginTop: 24 }}>
      {categories.map(c => <button key={c.slug} className={`category-tab ${category === c.slug ? 'active' : ''}`} onClick={() => setCategory(c.slug)}>
        <CatIcon category={c.slug} /> {c.name}
      </button>)}
    </div>
    <div className="dish-edit-row" style={{ alignItems: 'center', marginTop: 12 }}>
      <div className="dish-search" style={{ margin: 0, flex: 1 }}>
        <Search size={16} />
        <input placeholder={t.searchDish} value={search} onChange={e => setSearch(e.target.value)} />
      </div>
      <label className="dish-edit-checkbox"><input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)} /> {t.showInactive}</label>
    </div>
    {/* Tarjeta de edicion por platillo: se ampliaron los campos editables
        (antes solo nombre/precio/disponibilidad/guisado) para que el
        administrador pueda dejar listos TODOS los datos que se muestran en
        el menu animado publico: descripcion, medida/presentacion (para
        bebidas con mas de un tamano, ej. "355 ml" vs "600 ml") y la foto. */}
    {filteredDishes.map(d => <div className="dish-edit-card" key={d.id} style={d.is_active ? undefined : { opacity: 0.55 }}>
      <div className="dish-edit-row">
        <label className="dish-edit-field"><span>{t.dishTitle}</span><input defaultValue={d.title} onBlur={e => updateDish(d, 'title', e.target.value)} /></label>
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.price}</span><input type="number" defaultValue={d.price} onBlur={e => updateDish(d, 'price', Number(e.target.value))} /></label>
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.dishSize}</span><input placeholder="355 ml" defaultValue={d.size_label || ''} onBlur={e => updateDish(d, 'size_label', e.target.value)} /></label>
        <label className="dish-edit-field dish-edit-field-sm">
          <span>{t.schedule}</span>
          <select defaultValue={d.schedule} onChange={e => updateDish(d, 'schedule', e.target.value)}>
            <option value="all">{t.scheduleAll}</option>
            <option value="weekday">{t.scheduleWeekday}</option>
            <option value="weekend">{t.scheduleWeekend}</option>
            {[0, 1, 2, 3, 4, 5, 6].map(n => <option key={n} value={String(n)}>{t[`weekday${n}` as keyof Translations]}</option>)}
          </select>
        </label>
        <button className="ghost dish-edit-delete" title={d.is_active ? t.deactivate : t.reactivate} onClick={() => toggleDishActive(d)}>{d.is_active ? <Eye size={16} /> : <EyeOff size={16} />}</button>
      </div>
      <label className="dish-edit-field dish-edit-field-wide"><span>{t.dishDescription}</span><textarea rows={2} defaultValue={d.description || ''} onBlur={e => updateDish(d, 'description', e.target.value)} /></label>
      <div className="dish-edit-row">
        <label className="dish-edit-field dish-edit-field-wide"><span>{t.dishImageUrl}</span><input placeholder="https://..." defaultValue={d.image_url || ''} onBlur={e => updateDish(d, 'image_url', e.target.value)} /></label>
        <label className="dish-edit-checkbox"><input type="checkbox" defaultChecked={d.requires_guisado} onChange={e => updateDish(d, 'requires_guisado', e.target.checked)} /> {t.requiresGuisado}</label>
      </div>
    </div>)}
    {filteredDishes.length === 0 && <p className="empty-hint">{term ? t.noResultsSearch : t.empty}</p>}

    <h3 style={{ marginTop: 24 }}>{t.addDish}</h3>
    <div className="dish-edit-card">
      <div className="dish-edit-row">
        <label className="dish-edit-field"><span>{t.dishTitle}</span><input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label>
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.price}</span><input type="number" value={form.price} onChange={e => setForm({ ...form, price: e.target.value })} /></label>
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.dishSize}</span><input placeholder="355 ml" value={form.size_label} onChange={e => setForm({ ...form, size_label: e.target.value })} /></label>
        <label className="dish-edit-checkbox"><input type="checkbox" checked={form.requires_guisado} onChange={e => setForm({ ...form, requires_guisado: e.target.checked })} /> {t.requiresGuisado}</label>
      </div>
      <label className="dish-edit-field dish-edit-field-wide"><span>{t.dishDescription}</span><textarea rows={2} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
      <div className="dish-edit-row">
        <label className="dish-edit-field dish-edit-field-wide"><span>{t.dishImageUrl}</span><input placeholder="https://..." value={form.image_url} onChange={e => setForm({ ...form, image_url: e.target.value })} /></label>
        <button className="primary" onClick={addDish}><Plus size={16} /> {t.addDish}</button>
      </div>
    </div>

    <h3 style={{ marginTop: 30 }}>{t.guisados}</h3>
    <div className="pill-list">
      {guisados.map(g => <span className="pill-tag" key={g.id}>{g.name} <button className="pill-tag-remove" onClick={() => deleteGuisado(g.id)}>&times;</button></span>)}
    </div>
    <div className="inline-form-row" style={{ marginTop: 12 }}>
      <input placeholder={t.addGuisado} value={newGuisado} onChange={e => setNewGuisado(e.target.value)} />
      <button className="primary" onClick={addGuisado}><Plus size={16} /></button>
    </div>
  </section>;
}
