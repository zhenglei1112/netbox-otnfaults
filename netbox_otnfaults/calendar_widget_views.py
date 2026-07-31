from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_GET

from .dashboard import OtnCutoverCalendarWidget, OtnFaultsCalendarWidget


@login_required
@require_GET
def fault_calendar_fragment(request: HttpRequest) -> HttpResponse:
    """Render the fault calendar widget for the requested month."""
    return HttpResponse(OtnFaultsCalendarWidget().render(
        request,
        year_value=request.GET.get('year'),
        month_value=request.GET.get('month'),
        raise_errors=True,
    ))


@login_required
@require_GET
def cutover_calendar_fragment(request: HttpRequest) -> HttpResponse:
    """Render the cutover calendar widget for the requested month."""
    return HttpResponse(OtnCutoverCalendarWidget().render(
        request,
        year_value=request.GET.get('year'),
        month_value=request.GET.get('month'),
        raise_errors=True,
    ))
