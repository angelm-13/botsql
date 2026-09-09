"""La maquina de estados de Operaciones, servida a la interfaz.

Por que existe este archivo
---------------------------
Los tres procesos del modulo -proyectos, tareas e incidencias- tienen catalogo
de estatus, transiciones permitidas y motivos obligatorios, y los tres los
validan en el servidor (`operations_workflow` y `project_management_service`).
La interfaz no los leia de ningun sitio:

* la pantalla de proyectos llevaba su propia copia del mapa de transiciones
  escrita en JavaScript, asi que cualquier cambio en el servidor la dejaba
  ofreciendo un paso que ya no existia, o escondiendo uno nuevo;
* las de tareas e incidencias no lo tenian en absoluto y pintaban el estatus
  como un cuadro de texto libre. Las dos agrupan su tablero por ese campo, asi
  que un dedazo -"En Proceso " con mayuscula y espacio- creaba una columna
  nueva y el registro dejaba de aparecer donde su responsable lo buscaba.

Se sirve una sola respuesta con los tres catalogos: son lo mismo, se pintan
igual y quien abre el modulo los necesita a la vez.

No lleva `require_entity_permission` a proposito. No devuelve ni un dato de
negocio -solo la forma del flujo, que es la misma para todos- y exigir permiso
de una entidad concreta obligaria a elegir cual, dejando sin catalogo a quien
solo tiene la otra. El acceso a los registros lo sigue negando cada endpoint.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.services.operations_workflow import incident_catalog, task_catalog
from app.services.project_management_service import project_catalog
from app.utils.auth import token_required

bp_operations = Blueprint('operations', __name__, url_prefix='/operations')


@bp_operations.route('/catalog', methods=['GET'])
@token_required
def get_operations_catalog(user_data):
    return jsonify({
        'proyect': project_catalog(),
        'task': task_catalog(),
        'incident': incident_catalog(),
    })
