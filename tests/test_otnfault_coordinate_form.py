"""Exercise production coordinate fields and review template with Django alone."""
import ast
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest

try:
    from django import forms
    from django.template import Context, Engine
except ImportError:
    forms = None


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(forms is None, 'Django is required for form/render behavior tests')
class FaultCoordinateFormTests(unittest.TestCase):
    def setUp(self) -> None:
        from django.conf import settings

        if not settings.configured:
            settings.configure(USE_I18N=False, USE_TZ=True)
        tree = ast.parse((ROOT / 'netbox_otnfaults/forms.py').read_text(encoding='utf-8-sig'))
        form_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'OtnFaultForm')
        fields = {}
        for node in form_node.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name in ('interruption_latitude', 'interruption_longitude'):
                    fields[name] = eval(compile(ast.Expression(node.value), '<coordinate field>', 'eval'), {'forms': forms})
        self.form_class = type('CoordinateForm', (forms.Form,), fields)
        source = (ROOT / 'netbox_otnfaults/templates/netbox_otnfaults/otnfault_edit.html').read_text(encoding='utf-8-sig')
        self.review_line = next(line.strip() for line in source.splitlines() if 'const faultOpsManagerIds =' in line)

    def test_reversed_coordinates_show_field_error_and_render_unsaved_form(self) -> None:
        form = self.form_class(data={'interruption_latitude': '114', 'interruption_longitude': '34'})
        self.assertFalse(form.is_valid())
        self.assertIn('填反', str(form.errors['interruption_latitude']))
        self.assertIn('填反', str(form.errors['interruption_longitude']))

        class UnsavedFault:
            pk = None

            @property
            def operations_manager(self) -> object:
                raise ValueError('needs a value for field id')

        form.instance = UnsavedFault()
        rendered = Engine().from_string(self.review_line).render(Context({'form': form}))
        self.assertEqual(rendered, 'const faultOpsManagerIds = [];')
        # Prove this fixture reaches the original failure when the guard is removed.
        old_line = self.review_line.replace('{% if form.instance.pk %}', '').replace('{% endif %}', '')
        with self.assertRaises(ValueError):
            Engine().from_string(old_line).render(Context({'form': form}))

    def test_correct_coordinates_boundaries_and_empty_values(self) -> None:
        for lat, lng in [('34', '114'), ('18', '73'), ('54', '135'), ('34.123456', '114.123456'), ('', '')]:
            with self.subTest(lat=lat, lng=lng):
                form = self.form_class(data={'interruption_latitude': lat, 'interruption_longitude': lng})
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data['interruption_latitude'], Decimal(lat) if lat else None)

    def test_rejects_out_of_range_and_excess_precision(self) -> None:
        for field, value in [('interruption_latitude', '17.999999'), ('interruption_latitude', '54.000001'), ('interruption_longitude', '72.999999'), ('interruption_longitude', '135.000001'), ('interruption_latitude', '0'), ('interruption_longitude', '34'), ('interruption_latitude', '34.1234567')]:
            with self.subTest(field=field, value=value):
                form = self.form_class(data={field: value})
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_existing_fault_preserves_reviewer_ids(self) -> None:
        managers = SimpleNamespace(all=lambda: [SimpleNamespace(id=7), SimpleNamespace(id=12)])
        form = SimpleNamespace(instance=SimpleNamespace(pk=1, operations_manager=managers))
        rendered = Engine().from_string(self.review_line).render(Context({'form': form}))
        self.assertEqual(rendered, 'const faultOpsManagerIds = ["7","12",];')


if __name__ == '__main__':
    unittest.main()
