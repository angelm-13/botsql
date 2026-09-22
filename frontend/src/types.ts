/**
 * El contrato con el backend, escrito una sola vez.
 *
 * Estos tipos son un espejo de lo que devuelve `bi/service.py`. Si el backend
 * cambia la forma de la respuesta, el error aparece al compilar y no en una
 * pantalla en blanco delante de un usuario.
 */

export type TipoDeGrafica = "bar" | "line" | "pie" | "area" | "kpi_card" | "table";

export interface Visualizacion {
  chart_type: TipoDeGrafica;
  title: string;
  x_axis: string;
  y_axis: string;
  metric_label: string;
  recommended: boolean;
}

/** Una fila viene como objeto: las claves son los nombres de columna. */
export type Fila = Record<string, string | number | boolean | null>;

export interface ErrorDeWidget {
  tipo: string;
  motivo?: string;
  detalle?: string;
  mensaje?: string;
}

export interface Widget {
  ok: boolean;
  sql: string;
  explanation: string;
  visualization: Visualizacion;
  columnas: string[];
  filas: Fila[];
  total_filas: number;
  truncado: boolean;
  ms: number;
  advertencias: string[];
  error?: ErrorDeWidget;
}

export interface MetaBI {
  modelo?: string;
  ms_modelo?: number;
  ms_total?: number;
  tokens_prompt?: number;
  tokens_respuesta?: number;
  motor?: string;
  huella_esquema?: string;
  relaciones_expuestas?: number;
}

export interface ErrorBI {
  tipo: string;
  mensaje?: string;
  motivo?: string;
  detalle?: ErrorDeWidget | null;
  respuesta_cruda?: string;
}

export interface RespuestaBI {
  ok: boolean;
  pregunta: string;
  is_dashboard: boolean;
  dashboard_title: string;
  widgets: Widget[];
  meta: MetaBI;
  error?: ErrorBI;
}

/** Un turno de la consola: la pregunta y lo que contesto el servidor. */
export interface Turno {
  id: string;
  pregunta: string;
  estado: "cargando" | "listo" | "fallo";
  respuesta?: RespuestaBI;
  mensajeDeRed?: string;
}

export interface RelacionDelEsquema {
  nombre: string;
  tipo: "tabla" | "vista";
  columnas: { nombre: string; tipo: string; pk: boolean; fk: string | null }[];
  columnas_omitidas: string[];
}

export interface ResumenDeEsquema {
  motor: string;
  motor_legible: string;
  version: string;
  relaciones: RelacionDelEsquema[];
  total_encontradas: number;
  excluidas: string[];
  truncado: boolean;
  huella: string;
}
