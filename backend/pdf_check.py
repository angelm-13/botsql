from app import create_app, _documents_templates_dir, _load_quotation_document_record
app = create_app()
from documents.service import DocumentService   # create_app deja el path listo
with app.app_context():
    for clave in ("invoice_pdf", "quotation_pdf"):
        try:
            datos = DocumentService(_documents_templates_dir()).render_pdf_bytes(
                clave, _load_quotation_document_record(13), "es")
            print(f"  {clave:14s} {len(datos):>7} bytes  encabezado={datos[:5]!r}")
        except Exception as e:
            print(f"  {clave:14s} FALLA: {type(e).__name__}: {e}")
