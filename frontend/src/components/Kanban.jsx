import React, { useState } from 'react';
import "../styles/table.css";
import "../styles/button.css";

const Kanban = () => {
  const [lang] = useState(() => localStorage.getItem('language') || 'es');

  const translations = {
    es: {
      title: 'Tablero Kanban',
      todo: 'Por Hacer',
      inProgress: 'En Progreso',
      done: 'Completado'
    },
    en: {
      title: 'Kanban Board',
      todo: 'To Do',
      inProgress: 'In Progress',
      done: 'Done'
    }
  };

  const t_kanban = (key) => translations[lang]?.[key] || translations.es[key];

  return (
    <div style={{ padding: '20px' }}>
      <h1>{t_kanban('title')}</h1>
      <p>Componente Kanban - Implementación pendiente</p>
    </div>
  );
};

export default Kanban;
