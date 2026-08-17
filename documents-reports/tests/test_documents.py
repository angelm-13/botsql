from pathlib import Path
from app.documents.service import DocumentService
from app.documents.manifest import DOCUMENTS


def test_document_templates_render():
    service = DocumentService(Path(__file__).resolve().parents[2] / 'templates')
    for key, doc in DOCUMENTS.items():
        record = {field['name']: f"sample_{field['name']}" for field in doc['fields']}
        html = service.render_html(key, record, 'es')
        assert '<html' in html.lower()
        assert key in html
