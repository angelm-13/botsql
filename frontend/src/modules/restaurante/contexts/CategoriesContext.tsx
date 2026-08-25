import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '../services/api'
import type { Category } from '../types/api'

interface CategoriesContextValue {
  categories: Category[]
  reloadCategories: () => void
}

// Las categorias del menu ya no son un arreglo fijo en el codigo: se
// cargan una vez aqui y se comparten via contexto, porque CatIcon
// se usa en muchos puntos con distinta profundidad de anidamiento (menu
// del mesero, ticket, modal de estatus, pantalla de menu publico, panel
// de administracion) -- pasarlas por props ensuciaria toda esa cadena.
const CategoriesContext = createContext<CategoriesContextValue>({ categories: [], reloadCategories: () => {} })

export function useCategories(): CategoriesContextValue {
  return useContext(CategoriesContext)
}

export function CategoriesProvider({ children }: { children: ReactNode }) {
  const [categories, setCategories] = useState<Category[]>([])
  const reloadCategories = () => api.categories().then(d => setCategories(d.items || [])).catch(console.error)
  // Reintentos con backoff mientras `categories` siga vacio: el primer
  // intento se dispara justo cuando se monta la app, que puede coincidir
  // con el backend todavia arrancando (seed/migraciones en el primer
  // arranque de un despliegue). Antes, un 502/timeout en ese primer intento
  // dejaba `categories` vacio PARA SIEMPRE (el catch solo hacia
  // console.error, sin ningun mecanismo de reintento accesible para
  // mesero/cocina/cajero) -- sin categorias, MenuBrowser nunca podia
  // seleccionar una categoria activa, y el menu completo quedaba
  // bloqueado hasta que alguien recargara la pagina a mano. Se detiene
  // solo cuando la carga tiene exito (ver el .then de abajo).
  useEffect(() => {
    let cancelled = false
    let attempt = 0
    function attemptLoad() {
      api.categories()
        .then(d => { if (!cancelled) setCategories(d.items || []) })
        .catch(() => {
          if (cancelled) return
          attempt += 1
          const delay = Math.min(2000 * attempt, 15000)
          setTimeout(() => { if (!cancelled) attemptLoad() }, delay)
        })
    }
    attemptLoad()
    return () => { cancelled = true }
  }, [])
  return <CategoriesContext.Provider value={{ categories, reloadCategories }}>{children}</CategoriesContext.Provider>
}
