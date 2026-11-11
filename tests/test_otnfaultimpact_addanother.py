"""Execute the edit view in isolation without requiring a local NetBox install."""

import ast
from pathlib import Path
from secrets import token_urlsafe
from types import SimpleNamespace
from typing import Any
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class MultiDict(dict):
    def getlist(self, name: str) -> list[str]:
        value = self.get(name, [])
        return value if isinstance(value, list) else [value]


class BaseView:
    def post(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        return request.response

    def get_object(self, **kwargs: Any) -> Any:
        return SimpleNamespace(pk=kwargs.get('pk'), get_absolute_url=lambda: '/impacts/42/')

    def alter_object(self, obj: Any, *args: Any) -> Any:
        return obj

    def get_extra_context(self, *args: Any) -> dict:
        return {}


class Response(dict):
    def __init__(self, status: int = 302) -> None:
        super().__init__(Location='/impacts/add/')
        self.status_code = status


def load_view() -> type:
    tree = ast.parse((ROOT / 'netbox_otnfaults/views.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'OtnFaultImpactEditView')
    fault = SimpleNamespace(
        fault_occurrence_time='fault start', fault_recovery_time='fault recovery',
        interruption_location_a_id='default A',
        interruption_location=SimpleNamespace(values_list=lambda *a, **k: ['default Z']),
    )
    namespace = {
        'Any': Any, 'HttpRequest': Any,
        'generic': SimpleNamespace(ObjectEditView=BaseView),
        'OtnFaultImpact': SimpleNamespace(objects=SimpleNamespace(all=lambda: SimpleNamespace(model=object))),
        'OtnFaultImpactForm': lambda **kwargs: kwargs,
        'OtnFault': SimpleNamespace(objects=SimpleNamespace(get=lambda **kwargs: fault), DoesNotExist=LookupError),
        'ServiceTypeChoices': SimpleNamespace(CIRCUIT='circuit', BARE_FIBER='bare_fiber'),
        'reverse': lambda name: '/impacts/add/' if name.endswith('_add') else '/impacts/',
        'render': lambda request, template, context: context,
        'urlencode': urlencode, 'token_urlsafe': token_urlsafe,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<isolated edit view>', 'exec'), namespace)
    return namespace['OtnFaultImpactEditView']


class AddAnotherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.view = load_view()()
        # Set on the instance so the form stub is not bound as a method.
        self.view.form = lambda **kwargs: kwargs
        self.post = MultiDict(
            _addanother='', otn_fault='12', secondary_faults=['10', '11'],
            service_type='circuit', circuit_business_category='commercial',
            circuit_service_group='finance', circuit_special_line_name='55', circuit_service='55',
            bare_fiber_service='99', service_site_a='21', service_site_z=['22', '23'],
            business_impact='interrupted', service_interruption_time='2026-09-12 23:37:31',
            service_recovery_time='2026-11-13 09:18:14', coordination_status='approved',
            comments='第一行 & ?\n第二行', tags=['1', '2'],
        )

    def save(self, data: Any = None, status: int = 302, session: Any = None) -> Any:
        request = SimpleNamespace(
            POST=self.post if data is None else data,
            session={} if session is None else session, response=Response(status),
        )
        response = self.view.post(request)
        return request, response

    def follow(self, request: Any, response: Any, **kwargs: Any) -> dict:
        query = {k: v[0] for k, v in parse_qs(urlsplit(response['Location']).query).items()}
        return self.view.get(SimpleNamespace(GET=query, session=request.session), **kwargs)['form']['initial']

    def test_circuit_roundtrip_keeps_all_other_fields_including_both_sites(self) -> None:
        request, response = self.save()
        initial = self.follow(request, response)
        for name in (
            'otn_fault', 'secondary_faults', 'service_type', 'circuit_business_category',
            'circuit_service_group', 'service_site_a', 'service_site_z', 'business_impact',
            'service_interruption_time', 'service_recovery_time', 'coordination_status', 'comments', 'tags',
        ):
            self.assertEqual(initial[name], self.post[name], name)
        for name in ('circuit_special_line_name', 'circuit_service', 'bare_fiber_service'):
            self.assertNotIn(name, initial)
        self.assertNotIn('comments', response['Location'])
        self.assertEqual(initial, self.follow(request, response))  # Refresh retains defaults.

    def test_bare_fiber_keeps_its_business_and_sites_without_circuit_fields(self) -> None:
        self.post['service_type'] = 'bare_fiber'
        request, response = self.save()
        initial = self.follow(request, response)
        for name in ('bare_fiber_service', 'service_site_a', 'service_site_z'):
            self.assertEqual(initial[name], self.post[name])
        self.assertFalse(any(name.startswith('circuit_') for name in initial))

    def test_empty_values_override_parent_fault_defaults(self) -> None:
        for name in ('service_interruption_time', 'service_recovery_time', 'service_site_a', 'comments'):
            self.post[name] = ''
        for name in ('secondary_faults', 'service_site_z', 'tags'):
            del self.post[name]
        request, response = self.save()
        initial = self.follow(request, response)
        self.assertEqual(initial['service_recovery_time'], '')
        self.assertEqual(initial['service_site_a'], '')
        self.assertEqual(initial['service_site_z'], [])
        self.assertEqual(initial['secondary_faults'], [])
        self.assertEqual(initial['tags'], [])

    def test_invalid_save_and_normal_save_do_not_store_initial(self) -> None:
        request, _ = self.save(status=200)
        self.assertEqual(request.session, {})
        del self.post['_addanother']
        request, _ = self.save()
        self.assertEqual(request.session, {})

    def test_ordinary_add_edit_changed_fault_and_other_session_ignore_repeat(self) -> None:
        request, response = self.save()
        self.assertNotIn('comments', self.follow(request, response, pk=42))
        other = SimpleNamespace(session={})
        self.assertNotIn('comments', self.follow(other, response))
        query = {'otn_fault': '13', '_repeat': parse_qs(urlsplit(response['Location']).query)['_repeat'][0]}
        context = self.view.get(SimpleNamespace(GET=query, session=request.session))
        self.assertNotIn('comments', context['form']['initial'])
        context = self.view.get(SimpleNamespace(GET={}, session=request.session))
        self.assertEqual(context['form']['initial'], {})

    def test_tabs_are_independent_and_session_history_is_bounded(self) -> None:
        request, first = self.save()
        self.post['comments'] = 'other tab'
        _, second = self.save(session=request.session)
        self.assertNotEqual(first['Location'], second['Location'])
        self.assertNotEqual(self.follow(request, first)['comments'], self.follow(request, second)['comments'])
        for _ in range(12):
            self.save(session=request.session)
        self.assertEqual(len(request.session[self.view.repeat_session_key]), 10)


if __name__ == '__main__':
    unittest.main()
