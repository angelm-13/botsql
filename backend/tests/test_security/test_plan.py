"""El plan del despliegue: que modulos compro este cliente.

Lo que estas pruebas fijan, en orden de importancia:

* **el plan manda sobre el rol, y tambien sobre el superusuario.** Es la
  diferencia entre un permiso y una compra: un modulo fuera del plan no existe
  en este despliegue para nadie, y si el administrador pudiera alcanzarlo
  bastaria con concederse un rol para tener gratis lo que no pago;
* las capacidades cuentan igual que las entidades. El punto de venta y el
  restaurante se gatean con capacidades, no con tablas: sin cubrirlas, un
  cliente sin punto de venta seguiria entrando por el puente;
* configuracion y seguridad no se apagan nunca. Sin `status` los desplegables
  quedan vacios y sin `user` nadie administra: apagarlos por plan seria vender
  un sistema que no enciende;
* un nombre de modulo mal escrito detiene el arranque, en vez de apagar ese
  modulo en silencio.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.modules.plan import (
    MODULOS_SIEMPRE,
    Plan,
    PlanInvalido,
    plan_actual,
    reiniciar_plan,
)
from app.modules.registry import MODULOS_DE_NEGOCIO, modulo_de


RESTAURANTERO = {"modulos": ["facturacion", "inventario", "restaurante"]}


class TestQueDeclaraElPlan(unittest.TestCase):
    """El plan como dato, sin tocar base ni peticiones."""

    def test_a_plan_only_enables_what_it_lists(self):
        plan = Plan(RESTAURANTERO)
        self.assertTrue(plan.modulo_habilitado("restaurante"))
        self.assertFalse(plan.modulo_habilitado("pos"))
        self.assertFalse(plan.modulo_habilitado("logistica"))

    def test_infrastructure_is_never_off(self):
        """Sin catalogos ni usuarios no hay sistema que vender."""
        plan = Plan({"modulos": []})
        for clave in MODULOS_SIEMPRE:
            with self.subTest(modulo=clave):
                self.assertTrue(plan.modulo_habilitado(clave))
        self.assertTrue(plan.entidad_habilitada("status"))
        self.assertTrue(plan.entidad_habilitada("user"))

    def test_capabilities_count_like_entities(self):
        """La puerta del punto de venta es una capacidad, no una tabla.

        Sin esto, un cliente cuyo plan no trae el punto de venta seguiria
        alcanzando el puente: el puente se gatea con `pos_terminal` y
        `pos_admin`, y esas no son entidades de la base.
        """
        plan = Plan(RESTAURANTERO)
        self.assertFalse(plan.entidad_habilitada("pos_terminal"))
        self.assertFalse(plan.entidad_habilitada("pos_admin"))
        self.assertTrue(plan.entidad_habilitada("restaurant_admin"))
        self.assertTrue(plan.entidad_habilitada("inventory_adjustment"))

    def test_every_business_module_can_be_named_in_a_plan(self):
        """Un modulo que el plan no puede nombrar no se puede vender."""
        for clave in MODULOS_DE_NEGOCIO:
            with self.subTest(modulo=clave):
                self.assertTrue(Plan({"modulos": [clave]}).modulo_habilitado(clave))

    def test_a_misspelled_module_refuses_to_load(self):
        """Apagar un modulo en silencio es la peor forma de fallar.

        El cliente descubriria que no compro lo que compro al ir a usarlo.
        """
        with self.assertRaises(PlanInvalido):
            Plan({"modulos": ["facturacio"]})

    def test_no_plan_means_everything(self):
        """Es el caso de un despliegue nuestro y de las pruebas."""
        plan = Plan(None)
        self.assertTrue(plan.completo)
        for clave in MODULOS_DE_NEGOCIO:
            with self.subTest(modulo=clave):
                self.assertTrue(plan.modulo_habilitado(clave))

    def test_an_empty_module_list_is_not_the_same_as_no_plan(self):
        """`modulos: []` es un plan sin nada comprado, no un plan ausente."""
        vacio = Plan({"modulos": []})
        self.assertFalse(vacio.completo)
        self.assertFalse(vacio.modulo_habilitado("inventario"))

    def test_limits_travel_with_the_plan(self):
        plan = Plan({"modulos": ["inventario"], "limites": {"usuarios": 15}})
        self.assertEqual(15, plan.limite("usuarios"))
        # Lo que el plan no fija cae en el valor que pida quien pregunta.
        self.assertEqual(99, plan.limite("almacenamiento_gb", 99))

    def test_a_broken_plan_refuses_instead_of_guessing(self):
        for datos in ({"modulos": "facturacion"}, {"modulos": ["inventario"], "limites": []}):
            with self.subTest(datos=datos):
                with self.assertRaises(PlanInvalido):
                    Plan(datos)

    def test_it_is_read_from_the_deployment_configuration(self):
        reiniciar_plan()
        try:
            with patch.dict(os.environ, {"TYAKXA_PLAN": '{"modulos": ["inventario", "pos"]}'}):
                plan = plan_actual()
                self.assertTrue(plan.modulo_habilitado("pos"))
                self.assertFalse(plan.modulo_habilitado("restaurante"))
        finally:
            reiniciar_plan()


class TestElPlanManda(unittest.TestCase):
    """El plan por encima del rol, en los dos guardias."""

    def setUp(self):
        reiniciar_plan()
        self.entorno = patch.dict(os.environ, {"TYAKXA_PLAN": '{"modulos": ["facturacion", "inventario"]}'})
        self.entorno.start()

    def tearDown(self):
        self.entorno.stop()
        reiniciar_plan()

    def test_the_superuser_does_not_get_past_the_plan(self):
        """La prueba central de esta capa.

        El plan no es un permiso: es lo que el cliente compro. Si el
        administrador lo rebasara, tener gratis un modulo seria cuestion de
        concederse un rol.
        """
        from app.utils.auth import _has_entity_permission

        superusuario = {"id_user": 1, "is_superuser": True, "id_permission": 1}
        self.assertTrue(_has_entity_permission(superusuario, "product", "read"))
        self.assertFalse(_has_entity_permission(superusuario, "logistics_trip", "read"))
        self.assertFalse(_has_entity_permission(superusuario, "pos_terminal", "read"))

    def test_a_role_with_the_row_still_cannot_reach_it(self):
        """Cinturon y tirantes.

        El sembrador no crea las filas de un modulo fuera del plan, pero si
        alguien insertara una a mano -o si el plan se recorta despues de
        sembrar- la ruta tiene que seguir negando.
        """
        from app.utils.auth import _plan_permite

        self.assertFalse(_plan_permite("logistics_trip"))
        self.assertTrue(_plan_permite("invoice"))

    def test_an_entity_the_registry_does_not_know_is_let_through(self):
        """El plan no puede ser la razon por la que algo sin modulo se rompa."""
        from app.utils.auth import _plan_permite

        self.assertIsNone(modulo_de("entidad_que_no_existe"))
        self.assertTrue(_plan_permite("entidad_que_no_existe"))


if __name__ == "__main__":
    unittest.main()
