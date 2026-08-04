from datetime import datetime


def _remove_whitespace(value: object) -> str:
    """删除动态通报字段中的全部空白字符。"""
    return ''.join(str(value).split())


def _format_chinese_datetime(value: datetime) -> str:
    """以中文日期和不补零小时格式化时间。"""
    return (
        f'{value.year}年{value.month}月{value.day}日 '
        f'{value.hour}:{value.minute:02d}'
    )


def build_cutover_report_title(window_start: datetime, window_end: datetime) -> str:
    """生成包含起止时间的 24 小时割接预告标题。"""
    return (
        f'24小时割接预告（{_format_chinese_datetime(window_start)} 至 '
        f'{_format_chinese_datetime(window_end)}）'
    )


def build_cutover_report_line(
    *,
    item_number: int,
    province: object,
    cutover_type: object,
    reason: object,
    planned_time: datetime,
    impact_minutes: object,
    service_name: object,
    site_a: object,
    site_z: object,
    location: object,
) -> str:
    """按固定字段顺序生成单条结构化割接通报。"""
    service_name_text = _remove_whitespace(service_name)
    service_label = (
        service_name_text
        if service_name_text == '未关联业务'
        else f'{service_name_text}业务'
    )
    return (
        f'（{item_number}）{_remove_whitespace(province)}（{service_label}）\n'
        f'    割接类型：{_remove_whitespace(cutover_type)}\n'
        f'    计划时间：{_format_chinese_datetime(planned_time)}，'
        f'预计时长{_remove_whitespace(impact_minutes)}分钟\n'
        f'    中继段：A端{_remove_whitespace(site_a)}，'
        f'Z端{_remove_whitespace(site_z)}\n'
        f'    割接地点：{_remove_whitespace(location)}\n'
        f'    割接原因：{_remove_whitespace(reason)}'
    )
