import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.generic import View

from .services.shift_handover import generate_shift_handover_text


logger = logging.getLogger(__name__)


class ShiftHandoverGenerateView(LoginRequiredMixin, View):
    """Generate the current user's shift handover text without persisting it."""

    def get(self, request: HttpRequest) -> JsonResponse:
        shift_start_text = request.GET.get('shift_start', '')
        shift_start = parse_datetime(shift_start_text)
        if shift_start is None:
            return JsonResponse({'error': '班次开始时间格式无效。'}, status=400)

        if timezone.is_naive(shift_start):
            shift_start = timezone.make_aware(
                shift_start,
                timezone.get_current_timezone(),
            )
        else:
            shift_start = timezone.localtime(shift_start)

        try:
            now = timezone.localtime()
            text = generate_shift_handover_text(
                user=request.user,
                shift_start=shift_start,
                now=now,
            )
            return JsonResponse({'text': text})
        except Exception:
            logger.exception('Failed to generate shift handover text')
            return JsonResponse(
                {'error': '生成交接班内容失败，请稍后重试。'},
                status=500,
            )
