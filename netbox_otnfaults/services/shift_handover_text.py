from dataclasses import dataclass
from datetime import datetime, time, timedelta


SHIFT_HOURS: tuple[int, int] = (9, 18)


@dataclass(frozen=True)
class FaultHandoverItem:
    number: str
    occurred_at: datetime
    reason: str
    service_names: tuple[str, ...]
    handler: str
    progress_at: datetime | None
    progress_stage: str


@dataclass(frozen=True)
class CutoverHandoverItem:
    province: str
    cutover_type: str
    planned_at: datetime
    impact_minutes: int | None
    site_a: str
    site_z: tuple[str, ...]
    location: str
    reason: str
    bare_fiber_services: tuple[str, ...]


@dataclass(frozen=True)
class HeavyDutyHandoverItem:
    starts_at: datetime
    ends_at: datetime
    title: str
    description: str


def default_shift_start(now: datetime) -> datetime:
    """Return the default shift start using the local noon boundary."""
    is_afternoon = now.time() >= time(12)
    target_date = now.date() if is_afternoon else now.date() - timedelta(days=1)
    target_hour = 9 if is_afternoon else 18
    return now.replace(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=target_hour,
        minute=0,
        second=0,
        microsecond=0,
    )


def adjacent_shift_start(selected: datetime, *, direction: int) -> datetime:
    """Return the strictly previous or next 09:00/18:00 shift point."""
    if direction not in (-1, 1):
        raise ValueError('direction 必须为 -1 或 1')

    candidates = [
        selected.replace(hour=hour, minute=0, second=0, microsecond=0)
        + timedelta(days=offset)
        for offset in (-1, 0, 1)
        for hour in SHIFT_HOURS
    ]
    if direction == -1:
        return max(candidate for candidate in candidates if candidate < selected)
    return min(candidate for candidate in candidates if candidate > selected)


def handover_window_end(now: datetime) -> datetime:
    """Return 00:00 after the next calendar day (the next day at 24:00)."""
    target_date = now.date() + timedelta(days=2)
    return now.replace(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def latest_timeline_stage(
    stages: tuple[tuple[str, datetime | None], ...],
) -> tuple[str, datetime] | None:
    """Return the final populated stage in the configured timeline order."""
    for label, value in reversed(stages):
        if value is not None:
            return label, value
    return None


def _compact_text(value: object) -> str:
    """Remove horizontal whitespace from a database-derived display value."""
    text = str(value).strip() if value is not None else ''
    return ''.join(
        character
        for character in text
        if character in '\r\n' or not character.isspace()
    )


def _display(value: object) -> str:
    return _compact_text(value) or '-'


def _format_datetime(value: datetime) -> str:
    return (
        f'{value.year}年{value.month}月{value.day}日'
        f'{value.hour:02d}:{value.minute:02d}:{value.second:02d}'
    )


def _unique_text(values: tuple[str, ...]) -> str:
    unique_values = tuple(
        dict.fromkeys(
            compacted
            for value in values
            if (compacted := _compact_text(value))
        )
    )
    return '、'.join(unique_values) if unique_values else '-'


def _format_faults(faults: tuple[FaultHandoverItem, ...]) -> str:
    if not faults:
        return '无'

    lines: list[str] = []
    for index, fault in enumerate(faults, start=1):
        service_names = _unique_text(fault.service_names)
        impact = '线路组网' if service_names == '-' else f'{service_names}线路'
        progress = (
            f'{_format_datetime(fault.progress_at)}{_display(fault.progress_stage)}'
            if fault.progress_at is not None
            else '-'
        )
        lines.append(
            f'{index}、{_display(fault.number)}故障：因{_display(fault.reason)}导致中断，'
            f'目前正在处理，影响：{impact}，'
            f'处理人员{_display(fault.handler)}，处理进度：{progress}，请继续跟进。'
        )
    return '\n'.join(lines)


def _format_cutovers(
    cutovers: tuple[CutoverHandoverItem, ...],
    *,
    include_services: bool,
) -> str:
    if not cutovers:
        return '无'

    blocks: list[str] = []
    for index, cutover in enumerate(cutovers, start=1):
        impact_duration = (
            f'{cutover.impact_minutes}分钟'
            if cutover.impact_minutes is not None
            else '-'
        )
        lines = [
            f'（{index}）省份：{_display(cutover.province)}',
            f'割接类型：{_display(cutover.cutover_type)}',
            f'计划时间：{_format_datetime(cutover.planned_at)} 预计时长：{impact_duration}',
            f'中继段：{_display(cutover.site_a)}-{_unique_text(cutover.site_z)}',
            f'割接地点：{_display(cutover.location)}',
            f'割接原因：{_display(cutover.reason)}',
        ]
        if include_services:
            lines.append(f'影响业务：{_unique_text(cutover.bare_fiber_services)}')
        blocks.append('\n'.join(lines))
    return '\n'.join(blocks)


def _format_heavy_duties(
    items: tuple[HeavyDutyHandoverItem, ...],
    *,
    notice: bool,
) -> str:
    if not items:
        return '无'

    blocks: list[str] = []
    for index, item in enumerate(items, start=1):
        purpose = '通知' if notice else '要求线路重保'
        blocks.append(
            f'（{index}）{_format_datetime(item.starts_at)}至{_format_datetime(item.ends_at)}，'
            f'{_display(item.title)}{purpose}，具体信息描述：{_display(item.description)}'
        )
    return '\n'.join(blocks)


def build_handover_text(
    *,
    user_name: str,
    now: datetime,
    shift_start: datetime,
    faults: tuple[FaultHandoverItem, ...],
    bare_fiber_cutovers: tuple[CutoverHandoverItem, ...],
    other_cutovers: tuple[CutoverHandoverItem, ...],
    heavy_duties: tuple[HeavyDutyHandoverItem, ...],
    notices: tuple[HeavyDutyHandoverItem, ...],
) -> str:
    """Build the complete six-section shift handover text."""
    current_fault_count = sum(fault.occurred_at >= shift_start for fault in faults)
    historical_fault_count = len(faults) - current_fault_count
    cutoff_date = handover_window_end(now).date() - timedelta(days=1)

    sections = [
        f'接班人: {_display(user_name)}    截至{_format_datetime(now)}',
        (
            '一、故障移交（不含挂起）\n'
            f'本班移交待处理故障{current_fault_count}起，'
            f'另有前期班次移交需接续处理故障{historical_fault_count}'
            '起。（请在信息系统核对清点）'
        ),
        f'二、补充说明（值班留言）\n{_format_faults(faults)}',
        (
            f'三、今明割接任务（至{cutoff_date.year}年{cutoff_date.month}月'
            f'{cutoff_date.day}日24:00）\n'
            f'（一）影响裸纤业务\n{_format_cutovers(bare_fiber_cutovers, include_services=True)}\n'
            f'（二）仅影响电路业务\n{_format_cutovers(other_cutovers, include_services=False)}'
        ),
        f'四、重保事项\n{_format_heavy_duties(heavy_duties, notice=False)}',
        f'五、重要通知\n{_format_heavy_duties(notices, notice=True)}',
        '六、手机交接\n数量:  2        完好性: 正常  有损坏',
    ]
    return '\n\n'.join(sections)
