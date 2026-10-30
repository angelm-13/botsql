import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useI18n } from "../i18n";
import "../styles/task-board.css";

const HORA_PX = 44;
const HORAS_POR_OMISION = 1;
const MODOS = ["day", "week", "month"];

const inicioDelDia = (fecha) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
const sumarDias = (fecha, dias) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate() + dias);
const mismoDia = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
// La semana empieza en lunes.
const inicioDeSemana = (fecha) => sumarDias(inicioDelDia(fecha), -((fecha.getDay() + 6) % 7));

// Una tarea ocupa de `start_date` a `start_date + duration` horas (una hora si
// no trae duracion). Sin `start_date` no tiene lugar en el calendario.
export function intervaloDeTarea(tarea) {
  if (!tarea.start_date) return null;
  const inicio = new Date(tarea.start_date);
  if (Number.isNaN(inicio.getTime())) return null;
  const horas = Number(tarea.duration) > 0 ? Number(tarea.duration) : HORAS_POR_OMISION;
  return { inicio, fin: new Date(inicio.getTime() + horas * 3600000) };
}

function tareasDelDia(tareas, dia) {
  const desde = inicioDelDia(dia).getTime();
  const hasta = sumarDias(dia, 1).getTime();
  return tareas
    .map((tarea) => ({ tarea, intervalo: intervaloDeTarea(tarea) }))
    .filter(({ intervalo }) => intervalo && intervalo.inicio.getTime() < hasta && intervalo.fin.getTime() > desde)
    .map(({ tarea, intervalo }) => ({
      tarea,
      // Recortada al dia: lo que cruza la medianoche se corta en cada borde.
      minutoInicio: Math.max(0, (intervalo.inicio.getTime() - desde) / 60000),
      minutoFin: Math.min(1440, (intervalo.fin.getTime() - desde) / 60000),
    }))
    .sort((a, b) => a.minutoInicio - b.minutoInicio);
}

export default function TaskCalendar({ tareas, etiquetaResponsable, onSeleccionar }) {
  const { lang, t } = useI18n();
  const [modo, setModo] = useState("week");
  const [ancla, setAncla] = useState(() => inicioDelDia(new Date()));
  const hoy = new Date();
  const cuadricula = useRef(null);
  // Dia y semana abren hacia el inicio de la jornada, no a la medianoche.
  useEffect(() => { if (cuadricula.current) cuadricula.current.scrollTop = 7 * HORA_PX; }, [modo]);

  const formato = (opciones, fecha) => new Intl.DateTimeFormat(lang, opciones).format(fecha);
  const sinHorario = useMemo(() => tareas.filter((tarea) => !intervaloDeTarea(tarea)), [tareas]);

  function mover(pasos) {
    setAncla((actual) => (
      modo === "month" ? new Date(actual.getFullYear(), actual.getMonth() + pasos, 1)
        : sumarDias(actual, pasos * (modo === "week" ? 7 : 1))
    ));
  }

  const dias = useMemo(() => {
    if (modo === "day") return [ancla];
    if (modo === "week") return Array.from({ length: 7 }, (_, i) => sumarDias(inicioDeSemana(ancla), i));
    const primero = inicioDeSemana(new Date(ancla.getFullYear(), ancla.getMonth(), 1));
    return Array.from({ length: 42 }, (_, i) => sumarDias(primero, i));
  }, [modo, ancla]);

  const titulo = modo === "month" ? formato({ month: "long", year: "numeric" }, ancla)
    : modo === "day" ? formato({ dateStyle: "full" }, ancla)
    : `${formato({ day: "numeric", month: "short" }, dias[0])} – ${formato({ day: "numeric", month: "short", year: "numeric" }, dias[6])}`;

  const bloque = (item, compacto) => (
    <button
      type="button"
      key={item.tarea.id_task}
      className={`task-cal-item status-${item.tarea.task_status || "unknown"}`}
      style={compacto ? undefined : { top: (item.minutoInicio / 60) * HORA_PX, height: Math.max(((item.minutoFin - item.minutoInicio) / 60) * HORA_PX, 20) }}
      title={`${item.tarea.task_description} · ${etiquetaResponsable(item.tarea.owner)}`}
      onClick={() => onSeleccionar(item.tarea)}
    >
      {compacto ? "" : `${String(Math.floor(item.minutoInicio / 60)).padStart(2, "0")}:${String(Math.round(item.minutoInicio % 60)).padStart(2, "0")} `}
      {item.tarea.task_description}
    </button>
  );

  return (
    <div className="task-calendar">
      <div className="toolbar task-cal-toolbar">
        <button type="button" className="button" onClick={() => mover(-1)} aria-label={t("task_calendar.previous")}><ChevronLeft size={16} /></button>
        <button type="button" className="button" onClick={() => setAncla(inicioDelDia(new Date()))}>{t("task_calendar.today")}</button>
        <button type="button" className="button" onClick={() => mover(1)} aria-label={t("task_calendar.next")}><ChevronRight size={16} /></button>
        <strong className="task-cal-title">{titulo.charAt(0).toUpperCase() + titulo.slice(1)}</strong>
        {MODOS.map((m) => (
          <button type="button" key={m} className={modo === m ? "button active" : "button"} onClick={() => setModo(m)}>{t(`task_calendar.${m}`)}</button>
        ))}
      </div>

      {modo === "month" ? (
        <div className="task-cal-month">
          {dias.slice(0, 7).map((dia) => <div className="task-cal-weekday" key={dia.getDay()}>{formato({ weekday: "short" }, dia)}</div>)}
          {dias.map((dia) => {
            const delDia = tareasDelDia(tareas, dia);
            return (
              <div className={`task-cal-cell${dia.getMonth() !== ancla.getMonth() ? " outside" : ""}${mismoDia(dia, hoy) ? " today" : ""}`} key={dia.toISOString()}>
                <span className="task-cal-daynum">{dia.getDate()}</span>
                {delDia.slice(0, 3).map((item) => bloque(item, true))}
                {delDia.length > 3 && <small>+{delDia.length - 3}</small>}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="task-cal-grid" ref={cuadricula} style={{ gridTemplateColumns: `52px repeat(${dias.length}, minmax(0, 1fr))` }}>
          <div />
          {dias.map((dia) => (
            <div className={`task-cal-dayhead${mismoDia(dia, hoy) ? " today" : ""}`} key={dia.toISOString()}>{formato({ weekday: "short", day: "numeric" }, dia)}</div>
          ))}
          <div className="task-cal-hours">
            {Array.from({ length: 24 }, (_, h) => <span key={h} style={{ height: HORA_PX }}>{String(h).padStart(2, "0")}:00</span>)}
          </div>
          {dias.map((dia) => (
            <div className="task-cal-daycol" key={dia.toISOString()} style={{ height: 24 * HORA_PX }}>
              {tareasDelDia(tareas, dia).map((item) => bloque(item, false))}
            </div>
          ))}
        </div>
      )}

      {sinHorario.length > 0 && (
        <div className="task-cal-unscheduled">
          <strong>{t("task_calendar.unscheduled")} ({sinHorario.length})</strong>
          {sinHorario.map((tarea) => (
            <button type="button" key={tarea.id_task} className={`task-cal-item status-${tarea.task_status || "unknown"}`} onClick={() => onSeleccionar(tarea)}>{tarea.task_description}</button>
          ))}
        </div>
      )}
    </div>
  );
}
