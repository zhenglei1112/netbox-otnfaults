"""Opt-in, request-local statistics profiling without recording SQL or parameters."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from functools import wraps
from hashlib import sha256
import json
from time import perf_counter
from typing import Any, Callable, Iterator
from uuid import uuid4


_current: ContextVar[StatisticsProfile | None] = ContextVar('statistics_profile', default=None)


class StatisticsProfile:
    def __init__(self) -> None:
        self.started = perf_counter()
        self.request_id = uuid4().hex[:16]
        self.sql_count = 0
        self.sql_ms = 0.0
        self.stages: dict[str, dict[str, Any]] = {}
        self.sql_groups: dict[str, dict[str, Any]] = {}
        self.stack: list[str] = []
        self.child_ms: list[float] = []
        self.cache = 'not_applicable'

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started, sql_ms, sql_count = perf_counter(), self.sql_ms, self.sql_count
        key = '/'.join([*self.stack, name])
        self.stack.append(name)
        self.child_ms.append(0.0)
        try:
            yield
        finally:
            self.stack.pop()
            elapsed = (perf_counter() - started) * 1000
            children = self.child_ms.pop()
            if self.child_ms:
                self.child_ms[-1] += elapsed
            group = self.stages.setdefault(key, {'name': key, 'calls': 0, 'ms': 0.0, 'self_ms': 0.0, 'sql_ms': 0.0, 'sql_count': 0})
            group['calls'] += 1
            group['ms'] += elapsed
            group['self_ms'] += max(0, elapsed - children)
            group['sql_ms'] += self.sql_ms - sql_ms
            group['sql_count'] += self.sql_count - sql_count

    def execute(self, execute: Callable, sql: str, params: Any, many: bool, context: dict) -> Any:
        started = perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            elapsed = (perf_counter() - started) * 1000
            self.sql_count += 1
            self.sql_ms += elapsed
            # SQL text/parameters are deliberately never stored in diagnostics.
            fingerprint = sha256(str(sql).encode()).hexdigest()[:16]
            key = fingerprint + ':' + '/'.join(self.stack)
            if key not in self.sql_groups and len(self.sql_groups) >= 100:
                key = 'other'
            group = self.sql_groups.setdefault(key, {
                'fingerprint': fingerprint if key != 'other' else 'other',
                'stage': '/'.join(self.stack) if key != 'other' else 'other',
                'count': 0, 'ms': 0.0, 'max_ms': 0.0,
            })
            group['count'] += 1
            group['ms'] += elapsed
            group['max_ms'] = max(group['max_ms'], elapsed)

    def report(self, response_bytes: int = 0) -> dict[str, Any]:
        def rounded(rows: list[dict]) -> list[dict]:
            return [{k: round(v, 2) if isinstance(v, float) else v for k, v in row.items()} for row in rows]
        return {
            'request_id': self.request_id,
            'total_ms': round((perf_counter() - self.started) * 1000, 2),
            'sql_count': self.sql_count, 'sql_ms': round(self.sql_ms, 2),
            'response_bytes': response_bytes, 'cache': self.cache,
            'stages': rounded(sorted(self.stages.values(), key=lambda item: item['ms'], reverse=True)),
            'sql_top': rounded(sorted(self.sql_groups.values(), key=lambda item: item['ms'], reverse=True)[:20]),
        }


def statistics_stage(name: str) -> Callable:
    def decorate(func: Callable) -> Callable:
        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            profile = _current.get()
            if profile is None:
                return func(*args, **kwargs)
            label = name
            if name == 'group_statistics':
                label += ':supervisor' if kwargs.get('line_supervisor_scope') else ':branch_company'
            if name == 'comparison_period' and args:
                label += ':' + args[0].date().isoformat()
            with profile.stage(label):
                return func(*args, **kwargs)
        return wrapped
    return decorate


@contextmanager
def statistics_span(name: str) -> Iterator[None]:
    profile = _current.get()
    if profile is None:
        yield
    else:
        with profile.stage(name):
            yield


def statistics_cache(state: str) -> None:
    profile = _current.get()
    if profile is not None:
        profile.cache = state


def statistics_cache_bypass(request: Any) -> bool:
    return _current.get() is not None and request.GET.get('statistics_cache_bypass') == '1'


def diagnostics_allowed(request: Any, settings: Any) -> bool:
    configured = getattr(settings, 'PLUGINS_CONFIG', {}).get('netbox_otnfaults', {}).get('statistics_diagnostics', False)
    user = getattr(request, 'user', None)
    return bool(
        request.GET.get('statistics_debug') == '1'
        and (configured or getattr(settings, 'DEBUG', False))
        and user and getattr(user, 'is_authenticated', False)
        and (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))
    )


def statistics_debug_request(func: Callable) -> Callable:
    @wraps(func)
    def wrapped(self: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        from django.conf import settings
        if not diagnostics_allowed(request, settings):
            return func(self, request, *args, **kwargs)
        from django.db import connections
        profile = StatisticsProfile()
        token = _current.set(profile)
        try:
            with ExitStack() as stack:
                for alias in connections:
                    stack.enter_context(connections[alias].execute_wrapper(profile.execute))
                with profile.stage(self.__class__.__name__):
                    response = func(self, request, *args, **kwargs)
            report = profile.report(len(response.content))
            response['Server-Timing'] = f"statistics;dur={report['total_ms']}, sql;dur={report['sql_ms']}"
            response['X-Statistics-Request-ID'] = profile.request_id
            response['Cache-Control'] = 'private, no-store'
            if response.get('Content-Type', '').startswith('application/json'):
                payload = json.loads(response.content)
                if isinstance(payload, dict):
                    payload['_statistics_debug'] = report
                    response.content = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
            return response
        finally:
            _current.reset(token)
    return wrapped
