/**
 * Datos FIJOS para /dashboard-preview -- nunca pega a la API ni a la base.
 * Con la forma real que ya devuelven los KPIs nuevos de Adser (ver
 * backend/app/kpis/registry.py), no inventada al aire: los 44/19/28 de
 * "incidencias" y los 5 estados de material vienen del mismo lote que se
 * sembro con scripts/seed_kpi_incidencias_demo.py en esta misma sesion.
 */

export const EMPLEADOS_DEMO = [
  { id_user: 7, full_name: "Ana Torres" },
  { id_user: 8, full_name: "Luis Medina" },
  { id_user: 9, full_name: "Carla Ruiz" },
  { id_user: 10, full_name: "Jorge Paz" },
  { id_user: 11, full_name: "Sofía León" },
];

// Widget 1 -- numero: incidencias pendientes hoy vs. hace 30 dias.
export const INCIDENCIAS_PENDIENTES_DEMO = {
  valor: 19,
  variacion: -6, // hoy 19, hace 30 dias 25 -- bajar es bueno (direccion bajo_es_mejor)
  direccion: "bajo_es_mejor",
  tendencia: [25, 24, 23, 24, 22, 21, 22, 20, 21, 19, 20, 19, 18, 19],
};

// Widget 2 -- barras (2 series): abiertas vs. cerradas por semana, 13 semanas.
export const ABIERTAS_VS_CERRADAS_DEMO = [
  { semana: "S1", abiertas: 5, cerradas: 3 },
  { semana: "S2", abiertas: 4, cerradas: 4 },
  { semana: "S3", abiertas: 6, cerradas: 5 },
  { semana: "S4", abiertas: 3, cerradas: 4 },
  { semana: "S5", abiertas: 5, cerradas: 6 },
  { semana: "S6", abiertas: 2, cerradas: 3 },
  { semana: "S7", abiertas: 4, cerradas: 3 },
  { semana: "S8", abiertas: 3, cerradas: 4 },
  { semana: "S9", abiertas: 5, cerradas: 5 },
  { semana: "S10", abiertas: 2, cerradas: 4 },
  { semana: "S11", abiertas: 3, cerradas: 2 },
  { semana: "S12", abiertas: 1, cerradas: 3 },
  { semana: "S13", abiertas: 1, cerradas: 2 },
];

// Widget 3 -- barras (1 serie): incidencias abiertas por empleado, 30 dias.
export const INCIDENCIAS_POR_EMPLEADO_DEMO = EMPLEADOS_DEMO.map((empleado, indice) => ({
  id_user: empleado.id_user,
  empleado: empleado.full_name.split(" ")[0],
  nombreCompleto: empleado.full_name,
  cantidad: [8, 6, 5, 4, 3][indice],
}));

// Widget 4 -- tabla: material prestado ahora mismo.
export const MATERIAL_PRESTADO_DEMO = [
  { id: 1, articulo: "Taladro Bosch GSB 550", responsable: "Ana Torres", fecha_prestamo: "2026-09-05", dias_prestado: 23 },
  { id: 2, articulo: "Esmeriladora angular", responsable: "Luis Medina", fecha_prestamo: "2026-09-10", dias_prestado: 18 },
  { id: 3, articulo: "Multímetro Fluke 117", responsable: "Carla Ruiz", fecha_prestamo: "2026-09-20", dias_prestado: 8 },
  { id: 4, articulo: "Escalera de tijera 6 pies", responsable: "Jorge Paz", fecha_prestamo: "2026-09-22", dias_prestado: 6 },
  { id: 5, articulo: "Rotomartillo Makita", responsable: "Ana Torres", fecha_prestamo: "2026-08-30", dias_prestado: 29 },
  { id: 6, articulo: "Juego de desarmadores", responsable: "Sofía León", fecha_prestamo: "2026-09-24", dias_prestado: 4 },
  { id: 7, articulo: "Pulidora orbital", responsable: "Luis Medina", fecha_prestamo: "2026-09-26", dias_prestado: 2 },
  { id: 8, articulo: "Soldadora inversora", responsable: "Carla Ruiz", fecha_prestamo: "2026-09-08", dias_prestado: 20 },
];

// Widget 5 -- dona: material por estado. Colores FIJOS por categoria, iguales
// a `colores_categoria` de material_por_estado en el registry (backend) --
// no se inventan aqui, se copian para que la vista previa no se desincronice.
export const MATERIAL_POR_ESTADO_DEMO = [
  { categoria: "Salida", valor: 15, color: "#173b66" },
  { categoria: "Entrada", valor: 12, color: "#1b7a60" },
  { categoria: "Dañado", valor: 3, color: "#eda100" },
  { categoria: "Extraviado", valor: 2, color: "#e34948" },
  { categoria: "Destruccion", valor: 2, color: "#9b3030" },
];

export const KPIS_DEMO_PARA_EDITOR = [
  {
    clave: "incidencias_pendientes", etiqueta: "Incidencias pendientes", modulo: "operaciones",
    unidad: "numero", dimensiones: ["global"], direccion: "bajo_es_mejor",
    graficas_permitidas: ["numero"], grafica_default: "numero",
    descripcion: "Foto de cuantas incidencias siguen sin cerrar hoy.",
  },
  {
    clave: "incidencias_abiertas_vs_cerradas", etiqueta: "Incidencias abiertas vs. cerradas", modulo: "operaciones",
    unidad: "numero", dimensiones: ["estado"], direccion: "neutral",
    graficas_permitidas: ["barras", "linea"], grafica_default: "barras",
    descripcion: "Cuantas se abren y cuantas se cierran, por dia.",
  },
  {
    clave: "incidencias_abiertas_por_empleado", etiqueta: "Incidencias abiertas por empleado", modulo: "operaciones",
    unidad: "numero", dimensiones: ["empleado"], direccion: "neutral",
    graficas_permitidas: ["barras", "tabla"], grafica_default: "barras",
    descripcion: "Conteo de incidencias abiertas, por quien las levanto.",
  },
  {
    clave: "material_prestado_actual", etiqueta: "Material prestado ahora", modulo: "operaciones",
    unidad: "numero", dimensiones: ["empleado"], direccion: "neutral",
    graficas_permitidas: ["tabla"], grafica_default: "tabla",
    descripcion: "Renglones de vale prestados sin devolver, por responsable.",
  },
  {
    clave: "material_por_estado", etiqueta: "Material por estado", modulo: "operaciones",
    unidad: "numero", dimensiones: ["estado"], direccion: "neutral",
    graficas_permitidas: ["dona", "tabla"], grafica_default: "dona",
    descripcion: "Entrada, salida y disposiciones especiales de cada vale.",
  },
  {
    clave: "ventas_por_empleado", etiqueta: "Ventas por empleado", modulo: "facturacion",
    unidad: "moneda", dimensiones: ["empleado"], direccion: "alto_es_mejor",
    graficas_permitidas: ["numero", "barras", "linea", "area", "dona", "tabla"], grafica_default: "barras",
    descripcion: "Subtotal facturado, por empleado y por dia.",
  },
];
