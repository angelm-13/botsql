import { useCallback, useEffect, useRef, useState } from "react";
import { completarRespuesta, parametrosDeVivo, unirPaginas } from "../../kpi/kpiPrestamosServidor.js";

const ESPERA_BUSQUEDA_MS = 300;

/** El valor, pero solo despues de `espera` ms sin cambiar: una peticion por palabra escrita, no por tecla. */
function useConEspera(valor, espera) {
  const [estable, setEstable] = useState(valor);
  useEffect(() => {
    const temporizador = setTimeout(() => setEstable(valor), espera);
    return () => clearTimeout(temporizador);
  }, [valor, espera]);
  return estable;
}

const VACIO = { items: [], total: 0, resumen: null, responsables: [], cargando: false, cargandoMas: false, error: "" };

/** Los datos de la tabla de "Material prestado ahora" EN MODO SERVIDOR (ver kpi/kpiPrestamosServidor.js).
 *
 * Pide la primera pagina cada vez que cambia el responsable, el filtro de otra tarjeta, la busqueda, el
 * orden o la vista agrupada, y `cargarMas` pide la siguiente y la junta a lo ya cargado. Una respuesta que
 * llega tarde (de un filtro que ya cambio) se descarta: `generacion` dice cual peticion es la vigente.
 *
 * `cargar(parametros)` es la llamada al servidor (la pone el Dashboard); con `habilitado` falso el hook no
 * hace nada (el modo local de la tabla no lo usa). `onListo` se avisa UNA vez, cuando termina la primera
 * carga -con exito o con error-: el reporte PDF espera ese aviso para capturar la tarjeta.
 */
export default function useTablaServidor({
  habilitado, cargar, onListo, tamano, idUser, ambito, busqueda, orden, agrupada,
}) {
  const [estado, setEstado] = useState(() => ({ ...VACIO, cargando: Boolean(habilitado) }));
  const generacion = useRef(0);
  const avisado = useRef(false);
  const actual = useRef(estado);
  actual.current = estado;
  const cargarRef = useRef(cargar);
  cargarRef.current = cargar;
  const onListoRef = useRef(onListo);
  onListoRef.current = onListo;

  const busquedaEstable = useConEspera(busqueda, ESPERA_BUSQUEDA_MS);
  const ordenCampo = orden?.campo;
  const ordenDireccion = orden?.direccion;
  const clave = JSON.stringify([tamano, idUser, ambito, busquedaEstable, ordenCampo, ordenDireccion, Boolean(agrupada)]);

  useEffect(() => {
    if (!habilitado) return undefined;
    generacion.current += 1;
    const mia = generacion.current;
    setEstado((previo) => ({ ...previo, cargando: true, cargandoMas: false, error: "" }));
    const parametros = parametrosDeVivo({
      limit: tamano, offset: 0, idUser, ambito, busqueda: busquedaEstable,
      orden: { campo: ordenCampo, direccion: ordenDireccion }, agrupada,
    });
    cargarRef.current(parametros)
      .then((respuesta) => {
        if (mia !== generacion.current) return;
        setEstado({ ...completarRespuesta(respuesta), cargando: false, cargandoMas: false, error: "" });
      })
      .catch((error) => {
        if (mia !== generacion.current) return;
        setEstado((previo) => ({ ...previo, cargando: false, cargandoMas: false, error: error?.message || "errors.request_failed" }));
      })
      .finally(() => {
        if (mia !== generacion.current || avisado.current) return;
        avisado.current = true;
        onListoRef.current?.();
      });
    return undefined;
  // `clave` resume todos los filtros; el resto va por refs a proposito.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [habilitado, clave]);

  const cargarMas = useCallback(() => {
    const ahora = actual.current;
    if (!habilitado || ahora.cargando || ahora.cargandoMas || ahora.items.length >= ahora.total) return;
    const mia = generacion.current;
    setEstado((previo) => ({ ...previo, cargandoMas: true }));
    const parametros = parametrosDeVivo({
      limit: tamano, offset: ahora.items.length, idUser, ambito, busqueda: busquedaEstable,
      orden: { campo: ordenCampo, direccion: ordenDireccion }, agrupada,
    });
    cargarRef.current(parametros)
      .then((respuesta) => {
        if (mia !== generacion.current) return;
        setEstado((previo) => ({
          ...previo,
          items: unirPaginas(previo.items, respuesta.items),
          total: respuesta.total ?? previo.total,
          cargandoMas: false,
        }));
      })
      .catch((error) => {
        if (mia !== generacion.current) return;
        setEstado((previo) => ({ ...previo, cargandoMas: false, error: error?.message || "errors.request_failed" }));
      });
  }, [habilitado, tamano, idUser, ambito, busquedaEstable, ordenCampo, ordenDireccion, agrupada]);

  return {
    ...estado,
    hayMas: estado.items.length < estado.total,
    cargarMas,
  };
}
