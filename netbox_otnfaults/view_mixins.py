from __future__ import annotations

from typing import Any

from django.http import HttpResponse


class ExcelFriendlyCSVExportMixin:
    """Prepend a UTF-8 BOM so Excel opens exported CSV files without mojibake."""

    UTF8_BOM = b"\xef\xbb\xbf"

    def export_table(self, table: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        response = super().export_table(table, *args, **kwargs)
        content_type = response.get('Content-Type', '').lower()

        if 'text/csv' not in content_type or getattr(response, 'streaming', False):
            return response

        content = response.content
        if not content.startswith(self.UTF8_BOM):
            response.content = self.UTF8_BOM + content
            if response.has_header('Content-Length'):
                response['Content-Length'] = str(len(response.content))

        return response
