import unittest
import importlib.util
from pathlib import Path

from django.http import HttpResponse


MODULE_PATH = Path(__file__).resolve().parents[1] / 'netbox_otnfaults' / 'view_mixins.py'
SPEC = importlib.util.spec_from_file_location('test_view_mixins_module', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
ExcelFriendlyCSVExportMixin = MODULE.ExcelFriendlyCSVExportMixin


class _BaseExportView:
    def export_table(self, table, *args, **kwargs):
        response = HttpResponse('故障分类,光缆抖动\n', content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="faults.csv"'
        return response


class _DummyExportView(ExcelFriendlyCSVExportMixin, _BaseExportView):
    pass


class ExcelFriendlyCSVExportMixinTestCase(unittest.TestCase):
    def test_export_table_prepends_utf8_bom_for_csv_responses(self):
        response = _DummyExportView().export_table(table=None)

        self.assertEqual(response.content[:3], b'\xef\xbb\xbf')
        self.assertIn('故障分类'.encode('utf-8'), response.content)

    def test_export_table_leaves_non_csv_responses_unchanged(self):
        class _NonCSVBaseView:
            def export_table(self, table, *args, **kwargs):
                return HttpResponse('plain text', content_type='text/plain; charset=utf-8')

        class _NonCSVView(ExcelFriendlyCSVExportMixin, _NonCSVBaseView):
            pass

        response = _NonCSVView().export_table(table=None)

        self.assertEqual(response.content, b'plain text')


if __name__ == '__main__':
    unittest.main()
