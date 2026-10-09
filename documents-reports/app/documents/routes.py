from __future__ import annotations

from pathlib import Path
from flask import Blueprint, jsonify, make_response, request, send_file

from .manifest import DOCUMENTS
from .service import DocumentError, DocumentService


def create_documents_blueprint(templates_dir: str | Path, record_loader, access_checker=None):
    bp_documents = Blueprint('documents', __name__, url_prefix='/documents')
    service = DocumentService(templates_dir=templates_dir)

    @bp_documents.route('/manifest', methods=['GET'])
    def manifest():
        return jsonify({'documents': DOCUMENTS})

    @bp_documents.route('/<document_key>/<record_id>', methods=['GET'])
    def render_document(document_key: str, record_id: str):
        fmt = request.args.get('format', 'html')
        lang = request.args.get('lang', 'es')
        try:
            doc = DOCUMENTS.get(document_key)
            if not doc:
                raise DocumentError('document.not_found', {'document_key': document_key})
            if access_checker:
                allowed, status_code = access_checker(doc, record_id)
                if not allowed:
                    return jsonify({'error_key': 'errors.auth_required' if status_code == 401 else 'errors.permission_denied'}), status_code
            record = record_loader(doc['entity'], record_id)
            # issue_12_phase7_serve_original_xml
            if fmt == 'xml' and document_key == 'invoice_xml_cfdi':
                xml_text = record.get('_xml_original_text')
                if xml_text:
                    response = make_response(xml_text.encode('utf-8'))
                    response.headers['Content-Type'] = 'application/xml'
                    response.headers['Content-Disposition'] = f'inline; filename=invoice_xml_cfdi-{record_id}.xml'
                    return response
                xml_path = record.get('_xml_original_path') or record.get('xml_original_path')
                if xml_path and Path(xml_path).exists():
                    return send_file(
                        xml_path,
                        mimetype='application/xml',
                        as_attachment=False,
                        download_name=f'invoice_xml_cfdi-{record_id}.xml',
                    )
                raise DocumentError('document.xml_original_not_found', {'record_id': record_id})
            if fmt == 'pdf':
                payload = service.render_pdf_bytes(document_key, record, lang)
                response = make_response(payload)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'inline; filename={document_key}-{record_id}.pdf'
                return response
            html = service.render_html(document_key, record, lang)
            response = make_response(html)
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            return response
        except DocumentError as exc:
            return jsonify({'error_key': exc.code, 'details': exc.details}), 400

    return bp_documents
