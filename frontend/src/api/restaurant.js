import { request } from "./client";

export const getRestaurantWaiterWorkspace = () => request("/restaurant/waiter/bootstrap");
export const createRestaurantVisit = (payload) => request("/restaurant/waiter/visits", { method: "POST", body: payload });
export const getRestaurantVisit = (id) => request(`/restaurant/waiter/visits/${id}`);
export const addRestaurantDiner = (id) => request(`/restaurant/waiter/visits/${id}/diners`, { method: "POST" });
export const removeRestaurantDiner = (id, dinerIndex) => request(`/restaurant/waiter/visits/${id}/diners/${dinerIndex}`, { method: "DELETE" });
export const closeRestaurantVisit = (id) => request(`/restaurant/waiter/visits/${id}/close`, { method: "POST" });
export const addRestaurantOrderItem = (orderId, payload) => request(`/restaurant/waiter/orders/${orderId}/items`, { method: "POST", body: payload });
export const removeRestaurantOrderItem = (orderId, itemId) => request(`/restaurant/waiter/orders/${orderId}/items/${itemId}`, { method: "DELETE" });
export const sendRestaurantOrder = (orderId) => request(`/restaurant/waiter/orders/${orderId}/send`, { method: "POST" });
export const deliverRestaurantOrder = (orderId) => request(`/restaurant/waiter/orders/${orderId}/deliver`, { method: "POST" });
export const createRestaurantReservation = (payload) => request("/restaurant/waiter/reservations", { method: "POST", body: payload });

export const getRestaurantKitchenBoard = () => request("/restaurant/kitchen/board");
export const updateRestaurantKitchenOrder = (orderId, status) => request(`/restaurant/kitchen/orders/${orderId}/status`, { method: "PATCH", body: { status } });

export const getRestaurantCashierWorkspace = () => request("/restaurant/cashier/bootstrap");
export const getRestaurantReports = (params) => request("/restaurant/cashier/reports", { params });
export const payRestaurantOrder = (orderId, payload) => request(`/restaurant/cashier/orders/${orderId}/pay`, { method: "POST", body: payload });
export const openRestaurantRegister = (payload) => request("/restaurant/cashier/register/open", { method: "POST", body: payload });
export const closeRestaurantRegister = (payload) => request("/restaurant/cashier/register/close", { method: "POST", body: payload });

export const getRestaurantAdminWorkspace = () => request("/restaurant/admin/bootstrap");
export const createRestaurantDish = (payload) => request("/restaurant/admin/dishes", { method: "POST", body: payload });
export const updateRestaurantDish = (id, payload) => request(`/restaurant/admin/dishes/${id}`, { method: "PUT", body: payload });
export const createRestaurantGuisado = (payload) => request("/restaurant/admin/guisados", { method: "POST", body: payload });
export const createRestaurantTable = (payload) => request("/restaurant/admin/tables", { method: "POST", body: payload });
export const updateRestaurantTable = (id, payload) => request(`/restaurant/admin/tables/${id}`, { method: "PUT", body: payload });
export const createRestaurantWaiter = (payload) => request("/restaurant/admin/waiters", { method: "POST", body: payload });
export const updateRestaurantWaiter = (id, payload) => request(`/restaurant/admin/waiters/${id}`, { method: "PUT", body: payload });
export const deleteRestaurantCatalogItem = (kind, id) => request(`/restaurant/admin/${kind}/${id}`, { method: "DELETE" });
export const adminCreateRestaurantReservation = (payload) => request("/restaurant/admin/reservations", { method: "POST", body: payload });
export const createRestaurantInventoryItem = (payload) => request("/restaurant/admin/inventory", { method: "POST", body: payload });
export const createRestaurantRecipeItem = (payload) => request("/restaurant/admin/recipes", { method: "POST", body: payload });