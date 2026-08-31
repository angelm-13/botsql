import {
  Utensils, UtensilsCrossed, Flame, Wheat, Soup, Cake, GlassWater, CupSoda, Coffee, Candy,
  ChefHat, ShoppingBag, type LucideIcon,
} from 'lucide-react'
import { useCategories } from '../../contexts/CategoriesContext'

// Set curado de iconos que una categoria puede usar (ver CategoriesManager
// dentro de features/admin/DishesManager): no se guarda el componente de
// React en la base de datos, solo esta clave.
export const ICON_OPTIONS: Record<string, LucideIcon> = {
  utensils: Utensils, 'utensils-crossed': UtensilsCrossed, flame: Flame, wheat: Wheat,
  soup: Soup, cake: Cake, 'glass-water': GlassWater, 'cup-soda': CupSoda, coffee: Coffee,
  candy: Candy, 'chef-hat': ChefHat, 'shopping-bag': ShoppingBag,
}

export function CatIcon({ category, size = 18 }: { category?: string | null; size?: number }) {
  const { categories } = useCategories()
  const found = categories.find(c => c.slug === category)
  const Icon = (found?.icon && ICON_OPTIONS[found.icon]) || Utensils
  return <Icon size={size} style={{ color: found?.color || 'var(--brand-primary)' }} />
}
