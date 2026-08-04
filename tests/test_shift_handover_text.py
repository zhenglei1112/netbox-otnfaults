from datetime import datetime
import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / 'netbox_otnfaults' / 'services' / 'shift_handover_text.py'
SPEC = importlib.util.spec_from_file_location('shift_handover_text_under_test', MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError('无法加载交接班文本模块。')
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CutoverHandoverItem = MODULE.CutoverHandoverItem
FaultHandoverItem = MODULE.FaultHandoverItem
HeavyDutyHandoverItem = MODULE.HeavyDutyHandoverItem
adjacent_shift_start = MODULE.adjacent_shift_start
build_handover_text = MODULE.build_handover_text
default_shift_start = MODULE.default_shift_start
handover_window_end = MODULE.handover_window_end
latest_timeline_stage = MODULE.latest_timeline_stage


def test_default_shift_uses_previous_18_before_noon() -> None:
    assert default_shift_start(datetime(2026, 8, 4, 11, 59)) == datetime(2026, 8, 3, 18)


def test_default_shift_uses_today_09_from_noon() -> None:
    assert default_shift_start(datetime(2026, 8, 4, 12, 0)) == datetime(2026, 8, 4, 9)


def test_up_moves_to_previous_shift_and_down_to_next_shift() -> None:
    selected = datetime(2026, 8, 4, 9)

    assert adjacent_shift_start(selected, direction=-1) == datetime(2026, 8, 3, 18)
    assert adjacent_shift_start(selected, direction=1) == datetime(2026, 8, 4, 18)


def test_arrows_from_manual_time_choose_strict_adjacent_shift() -> None:
    selected = datetime(2026, 8, 4, 14, 30)

    assert adjacent_shift_start(selected, direction=-1) == datetime(2026, 8, 4, 9)
    assert adjacent_shift_start(selected, direction=1) == datetime(2026, 8, 4, 18)


def test_handover_window_ends_at_next_day_24() -> None:
    assert handover_window_end(datetime(2026, 8, 4, 14, 30)) == datetime(2026, 8, 6, 0)


def test_latest_timeline_stage_uses_last_populated_stage() -> None:
    stages = (
        ('故障起始', datetime(2026, 8, 4, 9)),
        ('处理派发', datetime(2026, 8, 4, 9, 5)),
        ('维修出发', None),
        ('到达现场', datetime(2026, 8, 4, 11)),
        ('故障恢复', None),
    )

    assert latest_timeline_stage(stages) == ('到达现场', datetime(2026, 8, 4, 11))


def test_latest_timeline_stage_returns_none_when_all_stages_are_empty() -> None:
    assert latest_timeline_stage((('故障起始', None), ('处理派发', None))) is None


def test_build_handover_text_renders_all_sections_and_missing_fields() -> None:
    now = datetime(2026, 8, 4, 14, 30)
    shift_start = datetime(2026, 8, 4, 9)
    faults = (
        FaultHandoverItem(
            number='F20260804001',
            occurred_at=datetime(2026, 8, 4, 10),
            reason='施工',
            service_names=('业务甲', '业务乙'),
            handler='张三',
            progress_at=datetime(2026, 8, 4, 11),
            progress_stage='到达现场',
        ),
        FaultHandoverItem(
            number='F20260803001',
            occurred_at=datetime(2026, 8, 3, 20),
            reason='',
            service_names=(),
            handler='',
            progress_at=datetime(2026, 8, 3, 20),
            progress_stage='故障起始',
        ),
    )
    bare_cutovers = (
        CutoverHandoverItem(
            province='四川',
            cutover_type='光缆割接',
            planned_at=datetime(2026, 8, 4, 20),
            impact_minutes=60,
            site_a='成都A站',
            site_z=('成都Z站',),
            location='成南高速K10',
            reason='迁改',
            bare_fiber_services=('裸纤甲', '裸纤甲'),
        ),
    )
    other_cutovers = (
        CutoverHandoverItem(
            province='',
            cutover_type='设备割接',
            planned_at=datetime(2026, 8, 5, 9),
            impact_minutes=None,
            site_a='西安A站',
            site_z=('西安Z1站', '西安Z2站'),
            location='',
            reason='',
            bare_fiber_services=(),
        ),
    )
    heavy_duties = (
        HeavyDutyHandoverItem(
            starts_at=datetime(2026, 8, 4, 8),
            ends_at=datetime(2026, 8, 5, 18),
            title='专项保障',
            description='加强线路巡检',
        ),
    )
    notices = (
        HeavyDutyHandoverItem(
            starts_at=datetime(2026, 8, 5, 9),
            ends_at=datetime(2026, 8, 5, 12),
            title='值班通知',
            description='保持电话畅通',
        ),
    )

    text = build_handover_text(
        user_name='李四',
        now=now,
        shift_start=shift_start,
        faults=faults,
        bare_fiber_cutovers=bare_cutovers,
        other_cutovers=other_cutovers,
        heavy_duties=heavy_duties,
        notices=notices,
    )

    assert text.startswith('接班人: 李四    截至2026年8月4日14:30:00')
    assert (
        '本班移交待处理故障1起，另有前期班次移交需接续处理故障1起。'
        '（请在信息系统核对清点）'
    ) in text
    assert '【当班新增故障，正在处理】' not in text
    assert '【非本班次故障即历史遗留】' not in text
    assert '影响：业务甲、业务乙线路，处理人员张三' in text
    assert '处理进度：2026年8月4日11:00:00到达现场' in text
    assert '因-导致中断' in text
    assert '影响：线路组网，处理人员-' in text
    assert '影响：-线路' not in text
    assert '三、今明割接任务（至2026年8月5日24:00）' in text
    assert '（一）影响裸纤业务\n（1）省份：四川' in text
    assert '中继段：成都A站-成都Z站' in text
    assert '影响业务：裸纤甲' in text
    assert '（二）仅影响电路业务\n（1）省份：-' in text
    assert '预计时长：-' in text
    circuit_section = text.split('（二）仅影响电路业务', 1)[1].split('四、重保事项', 1)[0]
    assert '影响业务：' not in circuit_section
    assert '专项保障要求线路重保，具体信息描述：加强线路巡检' in text
    assert '值班通知通知，具体信息描述：保持电话畅通' in text
    assert text.endswith('六、手机交接\n数量:  2        完好性: 正常  有损坏')


def test_build_handover_text_compacts_database_text_but_keeps_layout_spaces() -> None:
    text = build_handover_text(
        user_name='李 四',
        now=datetime(2026, 8, 4, 15, 51, 50),
        shift_start=datetime(2026, 8, 4, 9),
        faults=(
            FaultHandoverItem(
                number='F 001',
                occurred_at=datetime(2026, 8, 4, 10),
                reason='一 级\t原因',
                service_names=('华为 京汉广', '创景万通\t上海至深圳'),
                handler='张 三',
                progress_at=datetime(2026, 6, 18, 15, 59),
                progress_stage='处理 派发',
            ),
        ),
        bare_fiber_cutovers=(
            CutoverHandoverItem(
                province='四 川',
                cutover_type='光 缆割接',
                planned_at=datetime(2026, 8, 5, 8),
                impact_minutes=30,
                site_a='成 都A站',
                site_z=('成 都Z站',),
                location='成 南高速',
                reason='迁 改',
                bare_fiber_services=('华为 京汉广',),
            ),
        ),
        other_cutovers=(),
        heavy_duties=(
            HeavyDutyHandoverItem(
                starts_at=datetime(2026, 8, 5, 8),
                ends_at=datetime(2026, 8, 7, 23, 59, 59),
                title='重 保标题',
                description='重 保通知',
            ),
        ),
        notices=(),
    )

    assert text.startswith('接班人: 李四    截至2026年8月4日15:51:50')
    assert 'F001故障：因一级原因导致中断' in text
    assert '影响：华为京汉广、创景万通上海至深圳线路，处理人员张三' in text
    assert '处理进度：2026年6月18日15:59:00处理派发' in text
    assert '省份：四川\n割接类型：光缆割接' in text
    assert '计划时间：2026年8月5日08:00:00 预计时长：30分钟' in text
    assert '中继段：成都A站-成都Z站' in text
    assert '割接地点：成南高速\n割接原因：迁改\n影响业务：华为京汉广' in text
    assert (
        '（1）2026年8月5日08:00:00至2026年8月7日23:59:59，'
        '重保标题要求线路重保，具体信息描述：重保通知'
    ) in text
    assert text.endswith('六、手机交接\n数量:  2        完好性: 正常  有损坏')


def test_build_handover_text_keeps_empty_sections() -> None:
    text = build_handover_text(
        user_name='operator',
        now=datetime(2026, 8, 4, 10),
        shift_start=datetime(2026, 8, 3, 18),
        faults=(),
        bare_fiber_cutovers=(),
        other_cutovers=(),
        heavy_duties=(),
        notices=(),
    )

    assert (
        '本班移交待处理故障0起，另有前期班次移交需接续处理故障0起。'
        '（请在信息系统核对清点）'
    ) in text
    assert '二、补充说明（值班留言）\n无' in text
    assert '（一）影响裸纤业务\n无' in text
    assert '（二）仅影响电路业务\n无' in text
    assert '四、重保事项\n无' in text
    assert '五、重要通知\n无' in text


class ShiftHandoverTextTestCase(unittest.TestCase):
    test_default_shift_uses_previous_18_before_noon = staticmethod(
        test_default_shift_uses_previous_18_before_noon
    )
    test_default_shift_uses_today_09_from_noon = staticmethod(
        test_default_shift_uses_today_09_from_noon
    )
    test_up_moves_to_previous_shift_and_down_to_next_shift = staticmethod(
        test_up_moves_to_previous_shift_and_down_to_next_shift
    )
    test_arrows_from_manual_time_choose_strict_adjacent_shift = staticmethod(
        test_arrows_from_manual_time_choose_strict_adjacent_shift
    )
    test_handover_window_ends_at_next_day_24 = staticmethod(
        test_handover_window_ends_at_next_day_24
    )
    test_latest_timeline_stage_uses_last_populated_stage = staticmethod(
        test_latest_timeline_stage_uses_last_populated_stage
    )
    test_latest_timeline_stage_returns_none_when_all_stages_are_empty = staticmethod(
        test_latest_timeline_stage_returns_none_when_all_stages_are_empty
    )
    test_build_handover_text_renders_all_sections_and_missing_fields = staticmethod(
        test_build_handover_text_renders_all_sections_and_missing_fields
    )
    test_build_handover_text_compacts_database_text_but_keeps_layout_spaces = staticmethod(
        test_build_handover_text_compacts_database_text_but_keeps_layout_spaces
    )
    test_build_handover_text_keeps_empty_sections = staticmethod(
        test_build_handover_text_keeps_empty_sections
    )


if __name__ == '__main__':
    unittest.main()
