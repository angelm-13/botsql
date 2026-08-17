from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .manifest import DOCUMENTS


class DocumentError(Exception):
    def __init__(self, code: str, details: dict[str, Any] | None = None):
        super().__init__(code)
        self.code = code
        self.details = details or {}


class DocumentService:
    def __init__(self, templates_dir: str | Path, translations: dict[str, dict[str, str]] | None = None):
        self.templates_dir = Path(templates_dir)
        self.translations = translations or {}
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
        )

    def t(self, key: str, lang: str = 'es') -> str:
        return self.translations.get(lang, {}).get(key, key)

    @staticmethod
    def format_value(value: Any, value_format: str = 'text') -> str:
        if value is None:
            return '—'
        if value_format == 'currency':
            try:
                return f'${float(value):,.2f}'
            except Exception:
                return str(value)
        if value_format == 'date':
            return str(value)[:10]
        return str(value)

    def render_html(self, document_key: str, record: dict[str, Any], lang: str = 'es') -> str:
        if document_key not in DOCUMENTS:
            raise DocumentError('document.not_found', {'document_key': document_key})
        template = self.env.get_template(f'{document_key}.html')
        return template.render(
            lang=lang,
            record=record,
            generated_at=datetime.now(timezone.utc).isoformat(),
            t=lambda key: self.t(key, lang),
            format_value=self.format_value,
        )

    def render_pdf_bytes(self, document_key: str, record: dict[str, Any], lang: str = 'es') -> bytes:
        html = self.render_html(document_key, record, lang)
        try:
            from weasyprint import HTML
            return HTML(string=html, base_url=str(self.templates_dir)).write_pdf()
        except Exception as exc:
            raise DocumentError('document.pdf_renderer_unavailable', {'error': str(exc)}) from exc
