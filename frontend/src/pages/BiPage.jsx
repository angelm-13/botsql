import React, { useState, useEffect } from 'react';
import '../styles/bi-premium.css';

export default function BiPage() {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [queryHistory, setQueryHistory] = useState([]);
  const [cardAnimDelay, setCardAnimDelay] = useState(0);

  const handleQuerySubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setIsLoading(true);
    setError(null);
    setProgress(0);
    setResults(null);

    // Simular progreso
    const progressInterval = setInterval(() => {
      setProgress((prev) => Math.min(prev + Math.random() * 35, 95));
    }, 200);

    try {
      // Simular consulta (reemplazar con API real)
      await new Promise((resolve) => setTimeout(resolve, 2500));

      setProgress(100);
      setResults({
        sql: 'SELECT * FROM example_table LIMIT 10',
        rows: [
          { id: 1, name: 'Row 1', value: 100 },
          { id: 2, name: 'Row 2', value: 200 },
          { id: 3, name: 'Row 3', value: 150 },
        ],
        executionTime: 245,
        rowsReturned: 3,
      });

      // Agregar a historial
      setQueryHistory([
        { question, timestamp: new Date().toLocaleTimeString() },
        ...queryHistory.slice(0, 4),
      ]);

      setTimeout(() => setIsLoading(false), 500);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    } finally {
      clearInterval(progressInterval);
    }
  };

  const suggestedQueries = [
    '¿Cuántas facturas se emitieron este mes?',
    '¿Cuál es el producto más vendido?',
    '¿Total de ingresos por cliente?',
    '¿Inventario bajo alarma?',
  ];

  return (
    <div className="bi-container">
      {/* Header Premium */}
      <div className="bi-header">
        <div className="bi-header-content">
          <div className="bi-header-text">
            <h1 className="bi-title">
              <span className="bi-icon">✨</span> Análisis Inteligente de Datos
            </h1>
            <p className="bi-subtitle">Pregunta en lenguaje natural. Obtén insights al instante.</p>
          </div>
        </div>
      </div>

      <div className="bi-main">
        {/* Query Input Section */}
        <div className="bi-query-section">
          <form onSubmit={handleQuerySubmit} className="bi-form">
            <div className="bi-input-wrapper">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="¿Cuál es tu pregunta? (ej: Total de ventas este mes)"
                className={`bi-input ${isLoading ? 'bi-input-disabled' : ''}`}
                disabled={isLoading}
              />
              <button
                type="submit"
                className={`bi-submit-btn ${isLoading ? 'bi-submit-loading' : ''}`}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="bi-spinner"></span>
                    Procesando...
                  </>
                ) : (
                  <>
                    <span className="bi-submit-icon">→</span>
                    Analizar
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Progress Bar */}
          {isLoading && (
            <div className="bi-progress-container">
              <div className="bi-progress-bar">
                <div className="bi-progress-fill" style={{ width: `${progress}%` }}></div>
              </div>
              <p className="bi-progress-text">{Math.round(progress)}% completado</p>
            </div>
          )}

          {/* Suggested Queries */}
          {!results && !isLoading && (
            <div className="bi-suggestions">
              <p className="bi-suggestions-title">Sugerencias:</p>
              <div className="bi-suggestion-chips">
                {suggestedQueries.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => setQuestion(q)}
                    className="bi-suggestion-chip"
                    style={{ animationDelay: `${i * 0.1}s` }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="bi-content">
          {/* Results Section */}
          {results && (
            <div className="bi-results-section">
              <div className="bi-results-header">
                <h2 className="bi-results-title">Resultados</h2>
                <div className="bi-metrics">
                  <div className="bi-metric">
                    <span className="bi-metric-label">Filas</span>
                    <span className="bi-metric-value">{results.rowsReturned}</span>
                  </div>
                  <div className="bi-metric">
                    <span className="bi-metric-label">Tiempo</span>
                    <span className="bi-metric-value">{results.executionTime}ms</span>
                  </div>
                </div>
              </div>

              {/* SQL Display */}
              <div className="bi-sql-display">
                <p className="bi-sql-label">SQL Generado:</p>
                <code className="bi-sql-code">{results.sql}</code>
              </div>

              {/* Data Table */}
              <div className="bi-table-wrapper">
                <table className="bi-table">
                  <thead>
                    <tr>
                      {Object.keys(results.rows[0] || {}).map((key) => (
                        <th key={key}>{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {results.rows.map((row, i) => (
                      <tr key={i} className="bi-table-row" style={{ animationDelay: `${i * 0.05}s` }}>
                        {Object.values(row).map((val, j) => (
                          <td key={j}>{val}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="bi-error-box">
              <span className="bi-error-icon">⚠️</span>
              <div>
                <p className="bi-error-title">Error en la consulta</p>
                <p className="bi-error-message">{error}</p>
              </div>
            </div>
          )}

          {/* Stats Cards */}
          {!results && !isLoading && !error && (
            <div className="bi-stats-grid">
              <div className="bi-stat-card bi-stat-card-1">
                <div className="bi-stat-icon">📊</div>
                <h3>Consultas Rápidas</h3>
                <p>Obtén respuestas en segundos</p>
              </div>
              <div className="bi-stat-card bi-stat-card-2">
                <div className="bi-stat-icon">🔒</div>
                <h3>Completamente Seguro</h3>
                <p>7 capas de validación SQL</p>
              </div>
              <div className="bi-stat-card bi-stat-card-3">
                <div className="bi-stat-icon">⚡</div>
                <h3>Cache Inteligente</h3>
                <p>&lt;15ms en consultas repetidas</p>
              </div>
              <div className="bi-stat-card bi-stat-card-4">
                <div className="bi-stat-icon">📈</div>
                <h3>Análisis Avanzado</h3>
                <p>Lenguaje natural a SQL</p>
              </div>
            </div>
          )}

          {/* Query History */}
          {queryHistory.length > 0 && !results && (
            <div className="bi-history-section">
              <h3 className="bi-history-title">Historial Reciente</h3>
              <div className="bi-history-list">
                {queryHistory.map((item, i) => (
                  <button
                    key={i}
                    className="bi-history-item"
                    onClick={() => setQuestion(item.question)}
                    style={{ animationDelay: `${i * 0.05}s` }}
                  >
                    <span className="bi-history-question">{item.question}</span>
                    <span className="bi-history-time">{item.timestamp}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
