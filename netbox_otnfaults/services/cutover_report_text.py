from datetime import datetime


def _remove_whitespace(value: object) -> str:
    """删除动态通报字段中的全部空白字符。"""
    return ''.join(str(value).split())


def build_cutover_report_line(
    *,
    province: object,
    reason: object,
    planned_time: datetime,
    impact_minutes: object,
    service_name: object,
    site_a: object,
    site_z: object,
) -> str:
    """按固定书面模板生成单条割接通报正文。"""
    time_text = (
        f'{planned_time.year}年{planned_time.month}月{planned_time.day}日'
        f'{planned_time:%H:%M}'
    )
    service_name_text = _remove_whitespace(service_name)
    business_impact_text = (
        '预计不影响在用裸纤及电路业务' if service_name_text == '未关联业务'
        else f'影响{service_name_text}业务'
    )
    return (
        f'{_remove_whitespace(province)}割接报备：'
        f'因{_remove_whitespace(reason)}影响，需实施光缆割接，'
        f'计划于{time_text}开始，'
        f'预计影响时长{_remove_whitespace(impact_minutes)}分钟，'
        f'{business_impact_text}，'
        f'A端{_remove_whitespace(site_a)}，'
        f'Z端{_remove_whitespace(site_z)}。'
    )
