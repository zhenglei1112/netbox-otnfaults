"""Cached weather acquisition, isolated from interactive dashboard requests."""
from datetime import datetime, timedelta, timezone as dt_timezone
from email.utils import parsedate_to_datetime
import time
from typing import Any
from uuid import uuid4

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from dcim.models import Site

from .weather_geometry import (DEFAULT_THRESHOLDS, collection, feature, hko_catalog,
                               hko_track, safe_hko_url, sample_key, timestamp, weather_risks)

PREFIX = 'otnfaults:weather:v1:'
MET_URL = 'https://api.met.no/weatherapi/locationforecast/2.0/compact'
HKO_URL = 'https://www.weather.gov.hk/wxinfo/currwx/tc_list.xml'
TTL = 172800


def configuration() -> dict[str, Any]:
    return settings.PLUGINS_CONFIG.get('netbox_otnfaults', {})


def site_rows(user: Any = None, *, sync: bool = False) -> Any:
    query = Site.objects.all() if sync else Site.objects.restrict(user, 'view')
    return query.exclude(latitude__isnull=True).exclude(longitude__isnull=True).order_by('pk').values(
        'id', 'name', 'latitude', 'longitude', 'region_id', 'region__name')


def province_samples(rows: Any) -> dict[str, str]:
    """One existing, central coordinate per configured province (Site.region)."""
    groups: dict[str, set[str]] = {}
    for row in rows:
        key = sample_key(row['latitude'], row['longitude'])
        if row.get('region_id') is not None and key is not None:
            groups.setdefault(str(row['region_id']), set()).add(key)
    result: dict[str, str] = {}
    for province, keys in groups.items():
        points = [(key, *map(float, key.split(','))) for key in sorted(keys)]
        lat = sum(point[1] for point in points) / len(points)
        lng = sum(point[2] for point in points) / len(points)
        result[province] = min(points, key=lambda point: ((point[1] - lat) ** 2 + (point[2] - lng) ** 2, point[0]))[0]
    return result


def fetch_resource(session: requests.Session, url: str, key: str,
                   now: datetime, *, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Honor HTTP cache validators; no redirects to unapproved hosts."""
    old = cache.get(key) or {}
    expiry = timestamp(old.get('expires'))
    if expiry and now < expiry:
        return old
    headers = {}
    if old.get('etag'):
        headers['If-None-Match'] = old['etag']
    if old.get('modified'):
        headers['If-Modified-Since'] = old['modified']
    time.sleep(0.5)
    with session.get(url, params=params, headers=headers, timeout=(5, 15),
                     allow_redirects=False, stream=True) as response:
        if response.status_code == 429:
            retry = response.headers.get('Retry-After', '600')
            try:
                delay = max(600, int(retry))
            except ValueError:
                try:
                    delay = max(600, int((parsedate_to_datetime(retry) - now).total_seconds()))
                except (ValueError, TypeError):
                    delay = 600
            cache.set(PREFIX + ('met-pause' if url == MET_URL else 'hko-pause'), True, delay)
            raise ValueError('Source rate limited')
        if response.status_code not in (200, 304):
            raise ValueError(f'Source HTTP {response.status_code}')
        if response.status_code == 304 and not old.get('body'):
            raise ValueError('304 without cached content')
        body = old.get('body', b'')
        if response.status_code == 200:
            chunks = bytearray()
            for chunk in response.iter_content(65536):
                chunks.extend(chunk)
                if len(chunks) > 2_000_000:
                    raise ValueError('Source response too large')
            body = bytes(chunks)
        expires = now + timedelta(minutes=10)
        try:
            advertised = parsedate_to_datetime(response.headers['Expires'])
            expires = max(expires, advertised)
        except (KeyError, ValueError, TypeError):
            pass
        for directive in response.headers.get('Cache-Control', '').split(','):
            if directive.strip().startswith('max-age='):
                try:
                    expires = max(expires, now + timedelta(seconds=int(directive.split('=')[1])))
                except ValueError:
                    pass
        result = {'body': body, 'expires': expires.isoformat(), 'checked': now.isoformat(),
                  'etag': response.headers.get('ETag', old.get('etag')),
                  'modified': response.headers.get('Last-Modified', old.get('modified'))}
        # The caller commits only after content passes schema validation.
        return result


def sync_weather() -> dict[str, Any]:
    """Called by a management command, never by the data view."""
    import json
    token = str(uuid4())
    lock = PREFIX + 'sync-lock'
    if not cache.add(lock, token, 3600):
        return {'skipped': 'sync already running'}
    started = time.monotonic()
    options = configuration()
    try:
        with requests.Session() as session:
            agent = options.get('dashboard_v2_weather_user_agent', '')
            session.headers['User-Agent'] = agent or 'NetBox-OTNFaults/1.0'
            samples = province_samples(site_rows(sync=True))
            cache.set(PREFIX + 'province-samples', samples, TTL)
            keys = sorted(set(samples.values()))
            cursor = cache.get(PREFIX + 'met-cursor')
            if cursor in keys:
                offset = keys.index(cursor) + 1
                keys = keys[offset:] + keys[:offset]
            failures = 0
            succeeded = 0
            # Explicit configuration is mandatory for MET's contact requirements.
            if not agent or not ('@' in agent or 'https://' in agent):
                failures = len(keys) or 1
            else:
                for index, key in enumerate(keys):
                    if cache.get(PREFIX + 'met-pause') or time.monotonic() - started > 3000:
                        failures += len(keys) - index
                        break
                    try:
                        now = timezone.now()
                        lat, lng = key.split(',')
                        raw = fetch_resource(session, MET_URL, PREFIX + 'raw-met:' + key, now,
                                             params={'lat': lat, 'lon': lng})
                        data = json.loads(raw['body'])
                        properties = data.get('properties', {})
                        series = properties.get('timeseries')
                        if (not isinstance(series, list) or not series
                                or not all(isinstance(step, dict) and timestamp(step.get('time')) and isinstance(step.get('data'), dict) for step in series)
                                or not timestamp(properties.get('meta', {}).get('updated_at'))):
                            raise ValueError('Invalid MET forecast')
                        cache.set(PREFIX + 'raw-met:' + key, raw, TTL)
                        cache.set(PREFIX + 'met:' + key, data, TTL)
                        succeeded += 1
                    except (requests.RequestException, ValueError, TypeError, AttributeError):
                        failures += 1
                    finally:
                        cache.set(PREFIX + 'met-cursor', key, TTL)
            now = timezone.now()
            previous = cache.get(PREFIX + 'met-status') or {}
            met_status = {'state': 'error' if failures else 'ready', 'failed_samples': failures,
                          'samples': len(keys), 'checked_at': now.isoformat(),
                          'updated_at': now.isoformat() if succeeded or not keys and not failures else previous.get('updated_at')}
            cache.set(PREFIX + 'met-status', met_status, TTL)
            hko_errors = 0
            old = cache.get(PREFIX + 'hko') or {'tracks': {}}
            try:
                if cache.get(PREFIX + 'hko-pause'):
                    raise ValueError('HKO rate limited')
                raw = fetch_resource(session, HKO_URL, PREFIX + 'raw-hko-list', now)
                catalog = hko_catalog(raw['body'])
                cache.set(PREFIX + 'raw-hko-list', raw, TTL)
                tracks = {}
                for cyclone in catalog:
                    try:
                        if not safe_hko_url(cyclone['url']) or cache.get(PREFIX + 'hko-pause'):
                            raise ValueError('HKO source unavailable')
                        key = PREFIX + 'raw-hko:' + cyclone['id']
                        track_raw = fetch_resource(session, cyclone['url'], key, now)
                        tracks[cyclone['id']] = hko_track(track_raw['body'], cyclone)
                        cache.set(key, track_raw, TTL)
                    except (requests.RequestException, ValueError, TypeError):
                        hko_errors += 1
                        if cyclone['id'] in old['tracks']:
                            tracks[cyclone['id']] = old['tracks'][cyclone['id']]
                old = {'tracks': tracks, 'updated_at': now.isoformat()}
                cache.set(PREFIX + 'hko', old, TTL)
            except (requests.RequestException, ValueError, TypeError):
                hko_errors += 1
            hko_status = {'state': 'error' if hko_errors else 'ready',
                          'updated_at': old.get('updated_at'), 'checked_at': now.isoformat()}
            cache.set(PREFIX + 'hko-status', hko_status, TTL)
            return {'weather': met_status, 'typhoon': hko_status}
    finally:
        if cache.get(lock) == token:
            cache.delete(lock)


def read_weather(user: Any) -> dict[str, Any]:
    now = timezone.now()
    limits = {**DEFAULT_THRESHOLDS, **configuration().get('dashboard_v2_weather_thresholds', {})}
    weather = []
    missing = False
    forecasts: dict[str, Any] = {}
    samples = cache.get(PREFIX + 'province-samples') or {}
    for row in site_rows(user):
        key = samples.get(str(row.get('region_id')))
        if key is None:
            missing = True
            continue
        if key not in forecasts:
            forecasts[key] = cache.get(PREFIX + 'met:' + key)
        forecast = forecasts[key]
        if not forecast:
            missing = True
            continue
        updated = forecast['properties']['meta']['updated_at']
        issued = timestamp(updated)
        if issued is None or now - issued > timedelta(hours=24):
            missing = True
            continue
        future = [timestamp(step.get('time')) for step in forecast['properties']['timeseries']]
        if not any(value and now <= value < now + timedelta(hours=24) for value in future):
            missing = True
            continue
        risks = weather_risks(forecast, now, limits)
        if risks:
            weather.append(feature({'type': 'Point', 'coordinates': [float(row['longitude']), float(row['latitude'])]},
                                   {'site_id': row['id'], 'name': row['name'], 'risks': risks,
                                    'icon': '-'.join(risk['kind'] for risk in risks),
                                    'updated_at': updated, 'source': 'MET Norway',
                                    'sampling': 'province', 'province': row.get('region__name') or '',
                                    'sample_coordinates': key}))
    met_status = dict(cache.get(PREFIX + 'met-status') or {'state': 'loading'})
    met_status = {key: value for key, value in met_status.items() if key in ('state', 'updated_at', 'checked_at')}
    if missing and met_status['state'] == 'ready':
        met_status['state'] = 'stale'
    typhoon = []
    hko_status = dict(cache.get(PREFIX + 'hko-status') or {'state': 'loading'})
    for track in (cache.get(PREFIX + 'hko') or {}).get('tracks', {}).values():
        issued = timestamp(track.get('issued'))
        if issued and now - issued <= timedelta(hours=24):
            typhoon.extend(track['features'])
        elif hko_status['state'] == 'ready':
            hko_status['state'] = 'stale'
    # A stopped sync must never continue reporting a live connection indefinitely.
    for status in (met_status, hko_status):
        checked = timestamp(status.get('checked_at'))
        if checked and now - checked > timedelta(minutes=30) and status['state'] == 'ready':
            status['state'] = 'stale'
    return {'weather': collection(weather), 'typhoon': collection(typhoon),
            'sources': {'weather': met_status, 'typhoon': hko_status}}
