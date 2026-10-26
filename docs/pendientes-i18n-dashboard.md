# Pendiente: casi todos los textos del Dashboard de KPIs no están en ningún idioma

Nota para el equipo (Alan, Tanya, Ángel). **No se arregló**: se documenta para decidir
cómo y cuándo. Medido el 2026-10-16 sobre `initAlan`.

## Qué pasa

`frontend/src/pages/Dashboard.jsx` pide cada texto con `tx("clave", "texto en español")`, que
resuelve `kpi_dashboard.<clave>` en el catálogo del idioma activo y, si no está, en el de
español, y si tampoco, usa el texto en español escrito en el código (`frontend/src/i18n/index.js`).

De las **150 claves literales** de `tx()` en `Dashboard.jsx`, **135 no existen en ningún
catálogo, ni siquiera en `es.json`**. Solo hay 15 entradas en `kpi_dashboard`, y son
exactamente las de la vista previa con datos de ejemplo y las del selector de KPI
(`example_*`, `selector_*`, `kpi_search_*`, `kpi_variables_group`, `kpi_color_choose`).

Consecuencia: con el idioma en inglés, portugués o alemán, casi todo el editor "Agregar
gráfico" y las tarjetas del Dashboard (títulos, pasos, filtros, comparación, avisos,
botones, mensajes de error) salen **en español**. En español nada se nota, porque el texto
de respaldo del código es el español: por eso nadie lo vio.

Además hay claves **dinámicas** que un recuento estático no ve: `range_<clave>` (rangos
relativos), `chart_type_<tipo>` (nombre del tipo de gráfica) y `compare_shift_<días>`
(desfase de comparación). Hoy tampoco tienen entrada.

## Cómo se midió (reproducible)

```bash
cd frontend/src && python3 - <<'EOF'
import json, re
src = open("pages/Dashboard.jsx").read()
claves = set(re.findall(r'\btx\(\s*"([a-z0-9_]+)"', src))
es = json.load(open("i18n/locales/es.json"))["kpi_dashboard"]
print(len(claves), "claves;", len([c for c in claves if c not in es]), "sin entrada en ningún idioma")
EOF
# 150 claves; 135 sin entrada en ningún idioma
```

## Qué sí vigila hoy una prueba

`frontend/src/kpi/vistaPreviaEjemplo.test.mjs` exige las claves `example_*`, `selector_*` y
todas las que `Dashboard.jsx` le pasa al selector en `textos={{ ... }}`, en es/en/pt/de. El
resto del Dashboard no tiene ninguna prueba de claves: por eso pudo crecer sin que nada fallara.

## Qué NO se hizo

Nada del código ni de los catálogos. No se movieron los 135 textos ni se tradujeron.

## Propuesta (sin implementar, para decidir)

1. **Que `es.json` sea la fuente**: extraer del código cada `tx("clave", "respaldo")` y volcarlo a
   `kpi_dashboard` de `es.json` (un script lo hace sin teclear 135 textos), de modo que el
   español deje de depender del texto escrito en el JSX.
2. **Traducir a en/pt/de** (hoy `pt` y `de` ni siquiera tienen todas las secciones de `en`).
3. **Una prueba que exija que cada `tx()` literal exista en los cuatro idiomas**, generalizando
   la que ya hay para el selector; las claves dinámicas se listan explícitamente en la prueba
   (`range_*`, `chart_type_*`, `compare_shift_*`) porque no se pueden descubrir leyendo el código.
4. **Decidir qué idiomas se soportan de verdad.** Existen catálogos mínimos de `ja`, `zh-Hans`,
   `zh-Hant` y `nah` (unos 2 KB cada uno) que caen a español en todo lo demás: ¿se prometen o se
   quitan del selector de idioma?

Riesgo bajo: es solo texto, sin tablas ni migraciones. El trabajo grande es la traducción, no el
código.
