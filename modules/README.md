# Módulos del proyecto TYAKXA

El proyecto es uno solo, con submódulos de negocio. Este archivo explica cuáles
son, quién es dueño de qué, y cómo entra un repositorio nuevo.

## Los ocho submódulos de negocio

| Módulo | Almacén propio | Dónde vive el código |
|---|---|---|
| **facturación** | — | en el repositorio (`backend/app/routes/invoice*`, `services/invoice*`, `services/cfdi*`) |
| **inventario** | sí | en el repositorio (`services/inventory_service.py`, `location_service.py`) |
| **operaciones** | — | en el repositorio (`services/project_management_service.py`, `task_service.py`, `incident_service.py`) |
| **logística** | sí | en el repositorio (`routes/logistics_*`, `services/logistics_*`) |
| **restaurante** | sí | submódulo git → [`restaurante/`](#restaurante) |
| **punto de venta** | sí, en su propia base | submódulo git → [`pos/`](#pos) |
| **CRM** | — | en el repositorio (`routes/customer_supplier.py`, `sales_catalog*`, `survey_*`) |
| **RH** | — | en el repositorio (`routes/payroll_*`, `kronos*`) |

Además hay dos módulos de infraestructura que no son de negocio:
**configuración** (catálogos compartidos que toda pantalla necesita leer) y
**seguridad** (usuarios, perfiles y bitácora, solo administración).

La pertenencia de cada entidad a su módulo está declarada en
[`backend/app/modules/registry.py`](../backend/app/modules/registry.py), que es
la única fuente de verdad. Ese archivo se niega a cargar si una entidad queda
sin módulo o en dos, y hay pruebas que comparan su lista contra las entidades
que el código protege de verdad.

## Los cuatro almacenes son independientes

Cuatro módulos tienen almacén propio y ninguno comparte tabla con otro:

```
inventario    location ──────────────► inventory_stock ──► inventory_ledger
                                       (producto × ubicación, piezas enteras)

logística     logistics_warehouse ──► logistics_location ──► logistics_inventory
                                       (SKU, con lote y número de serie)

restaurante   restaurant_inventory_item ──► restaurant_inventory_movement
                                       (insumo, consumido por receta)

punto         dentro de su propia base: pos_enterprise
de venta                               (artículo de mostrador, kardex,
                                        bloqueo de sobreventa)
```

Los tres primeros viven en la base del núcleo y está comprobado por prueba que
ningún servicio los cruza. El punto de venta va un paso más allá: lleva el suyo
en una base distinta, así que no se puede cruzar ni por una consulta mal
escrita.

No comparten tabla a propósito. Cada uno guarda algo distinto: logística
mercancía de terceros que hay que poder rastrear por lote y serie, inventario
material propio de obra que se cuenta en piezas enteras, el restaurante insumos
que se descuentan por receta, y el punto de venta artículo de mostrador con
kardex y bloqueo de sobreventa. Unificarlos obligaría a que los cuatro pierdan
lo que les es propio.

La consecuencia práctica: **conceder el módulo de inventario a un rol no le da
ninguno de los otros tres**. El único perfil que opera dos
almacenes es *Jefe de almacén*, y está declarado como tal; una prueba falla si
aparece otro por descuido.

## Permisos por módulo y acción

La matriz completa —qué puede hacer cada perfil en cada módulo, con las cuatro
acciones CRUD por separado— vive en el mismo registro y se siembra con:

```bash
python backend/scripts/seed_module_permissions.py database/migrations/<fecha>_matriz.sql
```

Criterios, para que se puedan discutir en lugar de adivinarse:

- Solo administración borra. Un borrado con contabilidad y almacén de por medio
  deja huecos que no se reconstruyen; el resto de los perfiles cancela,
  acredita o ajusta, que sí deja rastro.
- Quien opera un módulo lo captura; quien lo supervisa lo consulta.
- Todos los perfiles leen `configuración`: sin acceso de lectura a `status` los
  desplegables de cualquier pantalla salen vacíos.
- Una capacidad que el acceso al módulo no puede ejercer no se concede. Darle
  «ajustar existencias» a un perfil que solo consulta inventario es una fila
  que no sirve y que hace creer que puede ajustar.
- El almacenista opera el almacén pero no ajusta, y el jefe de taller ejecuta
  proyectos pero no los autoriza: quien mueve la mercancía no tapa su propio
  faltante, y quien ejecuta no se aprueba a sí mismo.

## Submódulos git

### pos/

- **Repositorio**: https://github.com/Tyakxa/POS.git
- **Rama**: `initAngm`
- **Qué es**: POS Enterprise, punto de venta multi-caja para una sucursal, con
  inventario propio (entradas, mermas, kardex, bloqueo de sobreventa), cortes de
  caja y KPIs en vivo.
- **Base de datos propia**: `pos_enterprise`. Ojo con el puerto: su `.env`
  pedía el 5433, que lo ocupa la base del núcleo (`tyakxa-db-1`); hay que
  darle otro.
- **No trae**: facturación fiscal (CFDI) ni multi-sucursal. La facturación del
  núcleo sí las tiene, así que si se necesita timbrar una venta del POS hay que
  decidir cuál de los dos emite; hoy no están conectados.

### restaurante/

- **Repositorio**: https://github.com/Tyakxa/demo_restaurante.git
- **Rama**: `plantilla-base`
- **Componentes**: `backend/` (Python/FastAPI), `frontend/` (React/TypeScript),
  `scripts/`, `Docs/`

## Trabajar con los submódulos

Después de clonar, para descargarlos todos:

```bash
git submodule update --init --recursive
```

Para traer la última versión de cada uno:

```bash
git submodule update --remote
```

## Agregar un repositorio como módulo

Tres pasos, en este orden. El tercero es el que suele olvidarse, y sin él el
módulo existe pero ningún usuario puede entrar:

```bash
git submodule add --branch <rama> <url-del-repo> modules/<nombre>
```

Luego se declara en el registro, agregando su entrada a `MODULOS` en
`backend/app/modules/registry.py` —con sus entidades, y con su cadena de
almacén si tiene uno— y se concede a los perfiles que corresponda en `ROLES`.

Y por último se regenera la matriz de permisos y se aplica como migración. Si se
salta este paso, las pruebas del registro fallan señalando exactamente qué
entidad quedó sin módulo, que es preferible a descubrirlo por una pantalla en
blanco.
