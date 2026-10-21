from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .manifest import DOCUMENTS


def _check_local_only(url: str, templates_dir: Path) -> None:
    """Lo unico que el PDF puede cargar: `data:` y archivos de las plantillas o de
    UPLOAD_ROOT. Un campo de texto libre (el logo) que llegue a `<img src>` no debe
    poder hacer que el servidor pida una URL interna ni lea un archivo ajeno."""
    from urllib.parse import unquote, urlparse

    parsed = urlparse(url)
    if parsed.scheme == 'data':
        return
    if parsed.scheme == 'file':
        target = Path(unquote(parsed.path)).resolve()
        roots = [Path(templates_dir).resolve(), Path(os.getenv('UPLOAD_ROOT', '/uploads')).resolve()]
        if any(target.is_relative_to(root) for root in roots):
            return
    raise ValueError(f'Recurso externo bloqueado en el PDF: {parsed.scheme or "?"}')


def _local_only_fetcher(templates_dir: Path):
    """`url_fetcher` de WeasyPrint. Desde la 66 es una clase (`URLFetcher`); antes, una funcion."""
    try:
        from weasyprint.urls import URLFetcher
    except ImportError:
        from weasyprint import default_url_fetcher

        def fetcher(url, *args, **kwargs):
            _check_local_only(url, templates_dir)
            return default_url_fetcher(url, *args, **kwargs)
        return fetcher

    class LocalOnly(URLFetcher):
        def fetch(self, url, headers=None):
            _check_local_only(url, templates_dir)
            return super().fetch(url, headers)
    return LocalOnly(allowed_protocols=('data', 'file'))


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
            return HTML(string=html, base_url=str(self.templates_dir),
                        url_fetcher=_local_only_fetcher(self.templates_dir)).write_pdf()
        except Exception as exc:
            raise DocumentError('document.pdf_renderer_unavailable', {'error': str(exc)}) from exc
