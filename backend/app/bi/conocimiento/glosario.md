# Glosario del negocio

## Vale
Un vale es una incidencia (tabla incident). Registra un movimiento de herramientas o material de almacen. Tiene un tipo (Prestamo Material, Jornada, Comida, Salida por Permiso o accidente, Vacaciones, Maternidad, Reparacion, Destruccion, Danado, Extraviado), un responsable y un estatus.

## Estatus de un vale
Un vale puede estar abierta, borrador, cancelado, cerrada, en espera o en transito. No existe un estatus llamado "vencido".

## Vale vencido
Un vale esta vencido o atrasado cuando sigue abierto y alguna de sus herramientas no se ha devuelto despues de su fecha limite (due_date). No es un estatus: se calcula comparando la fecha limite con hoy.

## Herramienta, articulo, producto
En el sistema son lo mismo: un producto del inventario con descripcion, cantidad existente y ubicacion. Las herramientas de un vale se registran como renglones con cantidad y direccion (entrada o salida).

## Proyecto
Un proyecto u orden de trabajo pasa por los estatus: borrador, autorizado, en proceso, esperando material, bloqueado, completado, entregado o rechazado. Tiene cliente, responsable, tareas y costo total.



## Empleado y usuario
Son la misma persona en el sistema: un usuario con un rol (permiso) que define a que modulos y datos accede.
