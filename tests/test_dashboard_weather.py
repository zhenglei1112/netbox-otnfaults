import ast
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('weather_geometry', ROOT / 'netbox_otnfaults/services/weather_geometry.py')
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)
NOW = datetime(2026, 9, 14, 12, tzinfo=timezone.utc)


def forecast(value: float = 10, when: datetime = NOW) -> dict[str, Any]:
    return {'properties': {'meta': {'updated_at': NOW.isoformat()}, 'timeseries': [
        {'time': when.isoformat(), 'data': {'instant': {'details': {'wind_speed': value, 'air_temperature': 35}},
                                          'next_1_hours': {'details': {'precipitation_amount': value}}}}]}}


class GeometryTests(unittest.TestCase):
    def test_thresholds_and_window(self) -> None:
        self.assertEqual([r['kind'] for r in geometry.weather_risks(forecast(), NOW)], ['rain', 'wind', 'heat'])
        self.assertEqual([r['kind'] for r in geometry.weather_risks(forecast(9.9), NOW)], ['heat'])
        self.assertEqual(geometry.weather_risks(forecast(20, NOW + timedelta(hours=24)), NOW), [])
        self.assertEqual(geometry.weather_risks(forecast(20, NOW - timedelta(seconds=1)), NOW), [])
        self.assertEqual(geometry.weather_risks(forecast(), NOW, {'rain': 11, 'wind': 11, 'heat': 36}), [])

    def test_missing_fields_and_six_hour_rain_are_not_hourly_rain(self) -> None:
        data = forecast()
        values = data['properties']['timeseries'][0]['data']
        values.pop('next_1_hours')
        values['next_6_hours'] = {'details': {'precipitation_amount': 60}}
        values['instant']['details'] = {'air_temperature': 0}
        self.assertEqual([r['kind'] for r in geometry.weather_risks(data, NOW)], ['cold'])
        self.assertEqual(geometry.weather_risks({}, NOW), [])

    def test_sampling_invalid_and_dedup(self) -> None:
        self.assertEqual(geometry.sample_key(30.001, 114.001), geometry.sample_key(30.002, 114.002))
        for lat, lng in [(None, 1), (91, 0), (1, 181), (float('nan'), 1)]:
            self.assertIsNone(geometry.sample_key(lat, lng))

    def test_xml_security_and_empty_catalog(self) -> None:
        self.assertEqual(geometry.hko_catalog(b'<TropicalCycloneList/>'), [])
        catalog = geometry.hko_catalog(b'<TropicalCycloneList><TropicalCyclone><TropicalCycloneURL>http://www.weather.gov.hk/wxinfo/currwx/hko_tctrack_2639.xml</TropicalCycloneURL></TropicalCyclone></TropicalCycloneList>')
        self.assertTrue(catalog[0]['url'].startswith('https://'))
        for body in [b'<html/>', b'<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]><TropicalCycloneList>&x;</TropicalCycloneList>']:
            with self.assertRaises(ValueError): geometry.hko_catalog(body)
        for url in ['https://evil.test/wxinfo/currwx/tc_list.xml', 'http://www.weather.gov.hk/wxinfo/currwx/tc_list.xml',
                    'https://www.weather.gov.hk:bad/wxinfo/currwx/tc_list.xml', 'https://user@www.weather.gov.hk/wxinfo/currwx/tc_list.xml']:
            self.assertFalse(geometry.safe_hko_url(url))

    def test_track_interpolation_not_an_observation(self) -> None:
        xml = f'''<TropicalCycloneTrack><BulletinHeader><BulletinTime>{NOW.isoformat()}</BulletinTime></BulletinHeader>
        <WeatherReport><PastInformation><Latitude>20N</Latitude><Longitude>120E</Longitude></PastInformation>
        <AnalysisInformation><Latitude>21N</Latitude><Longitude>121E</Longitude><Time>{NOW.isoformat()}</Time><Intensity>Typhoon</Intensity></AnalysisInformation>
        <ForecastInformation><Latitude>22N</Latitude><Longitude>122E</Longitude><Time>{(NOW + timedelta(hours=12)).isoformat()}</Time></ForecastInformation>
        </WeatherReport></TropicalCycloneTrack>'''.encode()
        track = geometry.hko_track(xml, {'id': '1', 'name': '测试'})
        self.assertEqual(len(track['features']), 4)
        self.assertEqual([f['properties']['kind'] for f in track['features']], ['past', 'forecast', 'center', 'forecast'])
        self.assertEqual(geometry.coordinate('21.5S', True), -21.5)
        self.assertNotIn('radius', str(track))


class MemoryCache:
    def __init__(self) -> None: self.data = {}
    def get(self, key: str) -> Any: return self.data.get(key)
    def set(self, key: str, value: Any, *args: Any) -> None: self.data[key] = value
    def add(self, key: str, value: Any, *args: Any) -> bool:
        if key in self.data: return False
        self.data[key] = value
        return True
    def delete(self, key: str) -> None: self.data.pop(key, None)


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = MemoryCache()
        source = (ROOT / 'netbox_otnfaults/services/dashboard_weather.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ('read_weather', 'site_rows', 'fetch_resource', 'sync_weather')]
        self.scope = {**vars(geometry), 'cache': self.cache, 'PREFIX': 'test:', 'TTL': 172800, 'MET_URL': 'met',
                      'requests': SimpleNamespace(Session=object), 'time': SimpleNamespace(sleep=lambda _: None),
                      'parsedate_to_datetime': parsedate_to_datetime, 'timezone': SimpleNamespace(now=lambda: NOW),
                      'configuration': lambda: {}, 'Any': Any}
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<weather-service>', 'exec'), self.scope)

    def test_sync_lock_and_independent_hko_with_met_not_configured(self) -> None:
        class Session:
            def __init__(self) -> None: self.headers = {}
            def __enter__(self) -> Any: return self
            def __exit__(self, *args: Any) -> None: pass
        calls = []
        self.scope.update({'requests': SimpleNamespace(Session=Session, RequestException=RuntimeError),
                           'uuid4': lambda: 'token', 'time': SimpleNamespace(monotonic=lambda: 0), 'HKO_URL': 'hko',
                           'site_rows': lambda **kwargs: [{'latitude': 30, 'longitude': 114}],
                           'fetch_resource': lambda *args, **kwargs: calls.append(args[1]) or {'body': b'<TropicalCycloneList/>'}})
        result = self.scope['sync_weather']()
        self.assertEqual(result['weather']['state'], 'error')
        self.assertEqual(result['typhoon']['state'], 'ready')
        self.assertEqual(calls, ['hko'])
        self.assertIsNone(self.cache.get('test:sync-lock'))
        self.cache.add('test:sync-lock', 'another-process')
        self.assertIn('skipped', self.scope['sync_weather']())
        self.assertEqual(calls, ['hko'])

    def test_read_filters_permissions_and_expires_forecasts(self) -> None:
        calls = []
        class Query:
            def restrict(self, user: Any, permission: str) -> Any: calls.append((user, permission)); return self
            def exclude(self, **kwargs: Any) -> Any: return self
            def order_by(self, *args: Any) -> Any: return self
            def values(self, *args: Any) -> list[Any]: return [{'id': 1, 'name': 'allowed', 'latitude': 30, 'longitude': 114}]
        self.scope['Site'] = SimpleNamespace(objects=Query())
        self.cache.set('test:met:30.00,114.00', forecast())
        self.cache.set('test:met-status', {'state': 'ready', 'samples': 999, 'checked_at': NOW.isoformat()})
        result = self.scope['read_weather']('viewer')
        self.assertEqual(calls, [('viewer', 'view')])
        self.assertEqual(result['weather']['features'][0]['properties']['site_id'], 1)
        self.assertNotIn('samples', result['sources']['weather'])
        self.cache.set('test:met:30.00,114.00', forecast(10, NOW - timedelta(hours=1)))
        result = self.scope['read_weather']('viewer')
        self.assertEqual(result['weather']['features'], [])
        self.assertEqual(result['sources']['weather']['state'], 'stale')

    def test_conditional_request_and_cache_hit(self) -> None:
        calls = []
        class Response:
            status_code = 304
            headers = {'Cache-Control': 'max-age=1800'}
            def __enter__(self) -> Any: return self
            def __exit__(self, *args: Any) -> None: pass
        def get(*args: Any, **kwargs: Any) -> Any: calls.append(kwargs); return Response()
        session = SimpleNamespace(get=get)
        self.cache.set('raw', {'body': b'old', 'etag': 'v1'})
        result = self.scope['fetch_resource'](session, 'met', 'raw', NOW)
        self.assertEqual(result['body'], b'old')
        self.assertEqual(calls[0]['headers'], {'If-None-Match': 'v1'})
        self.assertFalse(calls[0]['allow_redirects'])
        self.cache.set('raw', result)
        self.scope['fetch_resource'](session, 'met', 'raw', NOW)
        self.assertEqual(len(calls), 1)

    def test_rate_limit_records_source_backoff(self) -> None:
        class Response:
            status_code = 429
            headers = {'Retry-After': '1200'}
            def __enter__(self) -> Any: return self
            def __exit__(self, *args: Any) -> None: pass
        with self.assertRaises(ValueError):
            self.scope['fetch_resource'](SimpleNamespace(get=lambda *a, **k: Response()), 'met', 'raw', NOW)
        self.assertTrue(self.cache.get('test:met-pause'))
