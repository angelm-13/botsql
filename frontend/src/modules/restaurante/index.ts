// Módulo Restaurante - Exports principales

// Features (Aplicaciones por rol)
export * from './features/waiter/WaiterApp';
export * from './features/kitchen/KitchenBoard';
export * from './features/admin/AdminApp';

// Services
export * from './services/api';

// Types
export type {
  User, Table, Visit, Order, OrderItem, Dish, Category, Guisado,
  CashSession, Invoice, InventoryItem, InventoryMovement, Reservation,
  Paginated, DashboardData, KpisData, SalesReport, OrderStatus,
  PaymentMethod, InventoryMovementType, Role, LoginResponse
} from './types/api';

// Contextos
export { CategoriesProvider, useCategories } from './contexts/CategoriesContext';
export { ToastProvider, useToast } from './contexts/ToastContext';
export { ConfirmProvider, useConfirm } from './contexts/ConfirmContext';
