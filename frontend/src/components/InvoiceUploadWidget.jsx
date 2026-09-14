/**
 * InvoiceUploadWidget.jsx - Widget de carga XML CFDI para integrar en Invoice.jsx
 * 
 * Compatible con sistema de i18n del proyecto tyakxa
 * Diseñado para integrarse en componente Invoice generado
 */

import React, { useState, useEffect } from 'react';
import '../styles/button.css';
import '../styles/form.css';
import { request } from '../api/client';
import { useI18n } from '../i18n';

const InvoiceUploadWidget = () => {
  const { lang } = useI18n();
  const [files, setFiles] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadResults, setUploadResults] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showUploadForm, setShowUploadForm] = useState(false);

  // Translations
  const translations = {
    es: {
      title: 'Cargar Facturas XML (CFDI)',
      subtitle: 'Cargue archivos XML de facturas CFDI para procesarlas automáticamente',
      selectProject: 'Seleccionar Proyecto',
      automaticType: 'Clasificación automática',
      automaticTypeHint: 'Se comparará el RFC de la empresa principal con el emisor y receptor para clasificar cada factura como venta o compra.',
      selectFile: 'Seleccionar Archivos XML',
      uploadedFiles: 'Archivos cargados:',
      uploadButton: 'Cargar Facturas',
      cancelButton: 'Cancelar',
      removeFile: 'Eliminar',
      successMessage: 'Facturas cargadas exitosamente',
      errorNoProject: 'Por favor seleccione un proyecto',
      errorNoFiles: 'Por favor seleccione al menos un archivo XML',
      errorInvalidFormat: 'El archivo {filename} no es un XML válido',
      errorFileTooLarge: 'El archivo {filename} es muy grande (máx. 5MB)',
      errorLoadingProjects: 'Error cargando proyectos',
      dragDropArea: 'Arrastra archivos XML aquí o haz clic para seleccionar',
    },
    en: {
      title: 'Load XML Invoices (CFDI)',
      subtitle: 'Upload CFDI invoice XML files to process them automatically',
      selectProject: 'Select Project',
      automaticType: 'Automatic classification',
      automaticTypeHint: 'The principal company RFC will be compared with the issuer and receiver to classify each invoice as a sale or purchase.',
      selectFile: 'Select XML Files',
      uploadedFiles: 'Uploaded files:',
      uploadButton: 'Upload Invoices',
      cancelButton: 'Cancel',
      removeFile: 'Remove',
      successMessage: 'Invoices uploaded successfully',
      errorNoProject: 'Please select a project',
      errorNoFiles: 'Please select at least one XML file',
      errorInvalidFormat: 'The file {filename} is not a valid XML',
      errorFileTooLarge: 'The file {filename} is too large (max. 5MB)',
      errorLoadingProjects: 'Error loading projects',
      dragDropArea: 'Drag XML files here or click to select',
    },
    pt: {
      title: 'Carregar faturas XML (CFDI)',
      subtitle: 'Carregue arquivos XML de faturas CFDI para processá-las automaticamente',
      selectProject: 'Selecionar projeto',
      automaticType: 'Classificação automática',
      automaticTypeHint: 'O RFC da empresa principal será comparado com o emissor e o receptor para classificar cada fatura.',
      selectFile: 'Selecionar arquivos XML',
      uploadedFiles: 'Arquivos carregados:',
      uploadButton: 'Carregar faturas',
      cancelButton: 'Cancelar',
      removeFile: 'Remover',
      successMessage: 'Faturas carregadas com sucesso',
      errorNoProject: 'Selecione um projeto',
      errorNoFiles: 'Selecione pelo menos um arquivo XML',
      errorInvalidFormat: 'O arquivo {filename} não é um XML válido',
      errorFileTooLarge: 'O arquivo {filename} é muito grande (máx. 5MB)',
      errorLoadingProjects: 'Erro ao carregar projetos',
      dragDropArea: 'Arraste arquivos XML aqui ou clique para selecionar',
    },
    de: {
      title: 'XML-Rechnungen laden (CFDI)',
      subtitle: 'Laden Sie CFDI-XML-Rechnungen hoch, um sie automatisch zu verarbeiten',
      selectProject: 'Projekt auswählen',
      automaticType: 'Automatische Klassifizierung',
      automaticTypeHint: 'Die RFC des Hauptunternehmens wird mit Aussteller und Empfänger verglichen.',
      selectFile: 'XML-Dateien auswählen',
      uploadedFiles: 'Geladene Dateien:',
      uploadButton: 'Rechnungen hochladen',
      cancelButton: 'Abbrechen',
      removeFile: 'Entfernen',
      successMessage: 'Rechnungen erfolgreich hochgeladen',
      errorNoProject: 'Bitte wählen Sie ein Projekt aus',
      errorNoFiles: 'Bitte wählen Sie mindestens eine XML-Datei aus',
      errorInvalidFormat: 'Die Datei {filename} ist kein gültiges XML',
      errorFileTooLarge: 'Die Datei {filename} ist zu groß (max. 5MB)',
      errorLoadingProjects: 'Fehler beim Laden der Projekte',
      dragDropArea: 'XML-Dateien hierher ziehen oder zum Auswählen klicken',
    }
  };

  const t = (key, vars = {}) => {
    let value = translations[lang]?.[key] || translations.es[key] || key;
    for (const [k, v] of Object.entries(vars)) {
      value = value.replace(`{${k}}`, v);
    }
    return value;
  };

  // Cargar proyectos solo cuando el usuario abre el formulario de carga.
  // Evita disparar errores de permisos en roles que solo pueden leer facturas.
  useEffect(() => {
    if (showUploadForm) loadProjects();
  }, [showUploadForm]);

  const loadProjects = async () => {
    try {
      const data = await request('/proyect/', { params: { page: 1, per_page: 100 } });
      setProjects(Array.isArray(data) ? data : (data.items || data.data || []));
    } catch (err) {
      console.error('Error loading projects:', err);
      setError(t('errorLoadingProjects'));
    }
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    
    // Validar que sean XML
    const validFiles = selectedFiles.filter(f => {
      if (!f.name.toLowerCase().endsWith('.xml')) {
        setError(t('errorInvalidFormat', { filename: f.name }));
        return false;
      }
      if (f.size > 5 * 1024 * 1024) {
        setError(t('errorFileTooLarge', { filename: f.name }));
        return false;
      }
      return true;
    });

    setFiles([...files, ...validFiles]);
    setError(null);
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (!selectedProject) {
      setError(t('errorNoProject'));
      return;
    }

    if (files.length === 0) {
      setError(t('errorNoFiles'));
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      formData.append('id_proyect', selectedProject);

      const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const response = await fetch(`${baseUrl}/invoice/upload-xml`, {
        method: 'POST',
        body: formData,
        headers
      });

      const result = await response.json();

      if (response.ok) {
        setSuccess(t('successMessage'));
        setUploadResults(result);
        setFiles([]);
        setSelectedProject('');
        
        // Limpar mensajes después de 5 segundos
        setTimeout(() => {
          setSuccess(null);
          setShowUploadForm(false);
        }, 5000);
      } else {
        const detail = result.message
          || result.error_key
          || (Array.isArray(result.results)
            ? result.results.map(r => `${r.file || 'archivo'}: ${r.message || r.status}${r.meta ? ' ' + JSON.stringify(r.meta) : ''}`).join('; ')
            : 'Error al cargar las facturas');
        setError(detail);
      }
    } catch (err) {
      console.error('Error uploading files:', err);
      setError('Error al cargar las facturas: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ marginTop: '30px', padding: '15px', borderTop: '2px solid #ddd' }}>
      <h3>{t('title')}</h3>
      <p style={{ color: '#666', fontSize: '14px' }}>{t('subtitle')}</p>

      {!showUploadForm ? (
        <button
          className="btn btn-primary"
          onClick={() => setShowUploadForm(true)}
          style={{ marginBottom: '15px' }}
        >
          ➕ {t('title')}
        </button>
      ) : (
        <div style={{ 
          backgroundColor: '#f9f9f9', 
          padding: '15px', 
          borderRadius: '5px',
          marginBottom: '15px'
        }}>
          {/* Error Messages */}
          {error && (
            <div style={{
              backgroundColor: '#ffebee',
              color: '#c62828',
              padding: '10px',
              marginBottom: '15px',
              borderRadius: '3px',
              border: '1px solid #ef5350'
            }}>
              ⚠️ {error}
            </div>
          )}

          {/* Success Messages */}
          {success && (
            <div style={{
              backgroundColor: '#e8f5e9',
              color: '#2e7d32',
              padding: '10px',
              marginBottom: '15px',
              borderRadius: '3px',
              border: '1px solid #81c784'
            }}>
              ✓ {success}
            </div>
          )}

          {/* Project Selection */}
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              {t('selectProject')}
            </label>
            <select
              required
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '3px',
                fontSize: '14px'
              }}
            >
              <option value="">-- {t('selectProject')} --</option>
              {projects.map(proj => (
                <option key={proj.id_proyect} value={proj.id_proyect}>
                  {proj.name_proyect || proj.nombre_proyect || proj.name || `Proyecto #${proj.id_proyect}`}
                </option>
              ))}
            </select>
          </div>

          <div className="xml-classification-hint">
            <strong>{t('automaticType')}</strong>
            <span>{t('automaticTypeHint')}</span>
          </div>

          {/* File Input */}
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              {t('selectFile')}
            </label>
            <input
              type="file"
              multiple
              accept=".xml"
              onChange={handleFileSelect}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '3px'
              }}
            />
            <p style={{ color: '#999', fontSize: '12px', marginTop: '5px' }}>
              {t('dragDropArea')}
            </p>
          </div>

          {/* Selected Files List */}
          {files.length > 0 && (
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                {t('uploadedFiles')} ({files.length})
              </label>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {files.map((file, index) => (
                  <li key={index} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px',
                    backgroundColor: '#fff',
                    border: '1px solid #eee',
                    marginBottom: '5px',
                    borderRadius: '3px'
                  }}>
                    <span style={{ fontSize: '14px' }}>📄 {file.name}</span>
                    <button
                      onClick={() => removeFile(index)}
                      className="btn btn-danger"
                      style={{ padding: '4px 8px', fontSize: '12px' }}
                    >
                      {t('removeFile')}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Upload Results Table */}
          {uploadResults && Array.isArray(uploadResults.results) && (
            <div style={{ marginBottom: '15px' }}>
              <h4>📊 Resultados de Carga</h4>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '12px'
              }}>
                <thead>
                  <tr style={{ backgroundColor: '#f0f0f0' }}>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Archivo</th>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Estado</th>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Clasificación</th>
                  </tr>
                </thead>
                <tbody>
                  {uploadResults.results.map((result, idx) => (
                    <tr key={idx}>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>{result.file}</td>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>{result.status === 'created' ? '✓' : '✗'}</td>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>{result.invoice_direction ? `${result.invoice_direction} · ${result.items_count || 0} partidas` : result.message || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleUpload}
              disabled={loading || files.length === 0 || !selectedProject}
              className="btn btn-primary"
              style={{
                opacity: loading || files.length === 0 || !selectedProject ? 0.6 : 1,
                cursor: loading || files.length === 0 || !selectedProject ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? '⏳ Cargando...' : t('uploadButton')}
            </button>
            <button
              onClick={() => {
                setShowUploadForm(false);
                setFiles([]);
                setError(null);
              }}
              className="btn btn-secondary"
            >
              {t('cancelButton')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default InvoiceUploadWidget;
