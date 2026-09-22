/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base de la API del modulo. Por omision usa el proxy de Vite en /api/v1/bi. */
  readonly VITE_BI_API?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
