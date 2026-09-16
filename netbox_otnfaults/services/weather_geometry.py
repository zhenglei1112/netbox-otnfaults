"""Pure transformations for public weather data; no network or database access."""
from datetime import datetime, timedelta, timezone
import math
import re
from typing import Any
from urllib.parse import urlparse
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

DEFAULT_THRESHOLDS = {'rain': 10.0, 'wind': 10.0, 'heat': 35.0, 'cold': 0.0}
HKO_HOSTS = {'www.weather.gov.hk', 'www.hko.gov.hk'}


def timestamp(value: Any) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result if result.tzinfo else None
    except (TypeError, ValueError):
        return None


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool) or value == '':
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def sample_key(lat: Any, lng: Any) -> str | None:
    lat, lng = number(lat), number(lng)
    if lat is None or lng is None or abs(lat) > 90 or abs(lng) > 180:
        return None
    return f'{lat:.2f},{lng:.2f}'


def weather_risks(data: dict[str, Any], now: datetime,
                  thresholds: dict[str, float] | None = None) -> list[dict[str, Any]]:
    limits = dict(DEFAULT_THRESHOLDS)
    for key, raw in (thresholds or {}).items():
        value = number(raw)
        if key in limits and value is not None:
            limits[key] = value
    peaks: dict[str, dict[str, Any]] = {}
    end = now + timedelta(hours=24)
    for step in data.get('properties', {}).get('timeseries', []):
        when = timestamp(step.get('time'))
        if when is None or not now <= when < end:
            continue
        values = step.get('data', {})
        instant = values.get('instant', {}).get('details', {})
        # Never treat a six-hour accumulation as one-hour precipitation.
        rain = values.get('next_1_hours', {}).get('details', {}).get('precipitation_amount')
        fields = {'rain': rain, 'wind': instant.get('wind_speed'),
                  'heat': instant.get('air_temperature'), 'cold': instant.get('air_temperature')}
        for kind, raw in fields.items():
            value = number(raw)
            if value is None:
                continue
            meets = value <= limits[kind] if kind == 'cold' else value >= limits[kind]
            previous = peaks.get(kind)
            stronger = previous is None or (value < previous['value'] if kind == 'cold' else value > previous['value'])
            if meets and stronger:
                peaks[kind] = {'kind': kind, 'value': value, 'time': when.isoformat()}
    return [peaks[kind] for kind in DEFAULT_THRESHOLDS if kind in peaks]


def safe_hko_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (parsed.scheme == 'https' and parsed.hostname in HKO_HOSTS
                and parsed.port in (None, 443) and not parsed.username and not parsed.password
                and bool(re.fullmatch(r'/wxinfo/currwx/(tc_list|hko_tctrack_\d+)\.xml', parsed.path))
                and not parsed.query and not parsed.fragment)
    except ValueError:
        return False


def xml_root(content: bytes) -> Any:
    if len(content) > 2_000_000:
        raise ValueError('HKO XML too large')
    try:
        return ElementTree.fromstring(content, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (DefusedXmlException, ElementTree.ParseError) as error:
        raise ValueError('Unsafe or invalid HKO XML') from error


def hko_catalog(content: bytes) -> list[dict[str, str]]:
    root = xml_root(content)
    if root.tag != 'TropicalCycloneList':
        raise ValueError('Invalid HKO catalogue')
    records = []
    for node in root.findall('TropicalCyclone'):
        url = (node.findtext('TropicalCycloneURL') or '').strip()
        # HKO's live catalogue still publishes HTTP URLs. Upgrade only when
        # the resulting HTTPS URL passes the full host/path allowlist.
        if url.startswith('http://'):
            upgraded = 'https://' + url[len('http://'):]
            if safe_hko_url(upgraded):
                url = upgraded
        if not safe_hko_url(url):
            raise ValueError('Unexpected HKO track URL')
        records.append({'id': node.findtext('TropicalCycloneID') or '',
                        'name': node.findtext('TropicalCycloneChineseName') or node.findtext('TropicalCycloneEnglishName') or '',
                        'url': url})
    if len(records) > 100:
        raise ValueError('Unexpected HKO catalogue size')
    return records


def coordinate(value: str, latitude: bool) -> float | None:
    match = re.fullmatch(r'\s*([0-9]+(?:\.[0-9]+)?)\s*([NSEW])\s*', value.upper())
    if not match or match[2] not in ('NS' if latitude else 'EW'):
        return None
    result = float(match[1]) * (-1 if match[2] in 'SW' else 1)
    return result if abs(result) <= (90 if latitude else 180) else None


def feature(geometry: dict[str, Any], properties: dict[str, Any]) -> dict[str, Any]:
    return {'type': 'Feature', 'geometry': geometry, 'properties': properties}


def collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {'type': 'FeatureCollection', 'features': features}


def hko_track(content: bytes, cyclone: dict[str, str]) -> dict[str, Any]:
    root = xml_root(content)
    if root.tag != 'TropicalCycloneTrack':
        raise ValueError('Invalid HKO track')
    issued = root.findtext('BulletinHeader/BulletinTime') or ''
    if timestamp(issued) is None:
        raise ValueError('Missing HKO bulletin time')
    report = root.find('WeatherReport')
    if report is None:
        raise ValueError('Missing HKO report')
    common = {'cyclone_id': cyclone['id'], 'name': cyclone['name'], 'issued': issued, 'source': 'HKO'}
    groups: dict[str, list[dict[str, Any]]] = {}
    points = []
    for tag, kind in [('PastInformation', 'past'), ('AnalysisInformation', 'center'), ('ForecastInformation', 'forecast')]:
        group = []
        for node in report.findall(tag):
            lat = coordinate(node.findtext('Latitude') or '', True)
            lng = coordinate(node.findtext('Longitude') or '', False)
            if lat is None or lng is None:
                continue
            when = node.findtext('Time') or ''
            props = {**common, 'kind': kind, 'time': when,
                     'intensity': node.findtext('Intensity') or '', 'wind': node.findtext('MaximumWind') or ''}
            point = feature({'type': 'Point', 'coordinates': [lng, lat]}, props)
            group.append(point)
            if timestamp(when):
                points.append(point)
        groups[kind] = group
    if not groups['center']:
        raise ValueError('Missing HKO current position')
    lines = []
    for kind, group in [('past', groups['past'] + groups['center']), ('forecast', groups['center'] + groups['forecast'])]:
        coordinates = [item['geometry']['coordinates'] for item in group]
        if len(coordinates) > 1:
            lines.append(feature({'type': 'LineString', 'coordinates': coordinates}, {**common, 'kind': kind}))
    return {'issued': issued, 'features': lines + points}
