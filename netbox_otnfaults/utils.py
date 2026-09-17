from .models import FaultCategoryChoices, FaultStatusChoices


BOOTSTRAP_COLOR_HEX: dict[str, str] = {
    'dark': '#343a40',
    'gray': '#6c757d',
    'light-gray': '#aaacae',
    'blue': '#0d6efd',
    'indigo': '#6610f2',
    'purple': '#6f42c1',
    'pink': '#d63384',
    'red': '#dc3545',
    'orange': '#f5a623',
    'yellow': '#ffc107',
    'green': '#198754',
    'teal': '#20c997',
    'cyan': '#0dcaf0',
    'white': '#ffffff',
    'secondary': '#6c757d',
}


def get_hex_color(color_name: str | None) -> str:
    """Map NetBox/Bootstrap color names to Hex values."""
    return BOOTSTRAP_COLOR_HEX.get(color_name or '', '#6c757d')


def build_fault_colors_config() -> dict[str, dict[str, str]]:
    """Build the shared color config used by unified map pages."""
    return {
        'category_colors': {
            value: get_hex_color(color)
            for value, _label, color in FaultCategoryChoices.CHOICES
        },
        'category_names': {
            value: label
            for value, label, _color in FaultCategoryChoices.CHOICES
        },
        'status_colors': {
            value: get_hex_color(color)
            for value, _label, color in FaultStatusChoices.CHOICES
        },
        'status_names': {
            value: label
            for value, label, _color in FaultStatusChoices.CHOICES
        },
        'popup_status_colors': {
            key: get_hex_color(key)
            for key in ['orange', 'blue', 'yellow', 'green', 'gray', 'red', 'secondary', 'purple']
        },
    }


from dataclasses import dataclass

@dataclass
class RepeatFaultResult:
    kpi_repeat_ids: set[int]
    ui_repeat_ids: set[int]
    matched_preceding_faults: list


def detect_repeat_faults(faults, past_faults, preceding_faults=None) -> RepeatFaultResult:
    """
    高效重复故障判定算法。
    """
    faults_list = list(faults)
    past_list = list(past_faults)
    preceding_list = list(preceding_faults) if preceding_faults else []

    fault_ids_set = {f.id for f in faults_list if getattr(f, 'id', None)}

    # 去重合并候选故障，防止因上层传参重复导致候选集翻倍
    all_faults_map = {}
    for f in faults_list + past_list + preceding_list:
        if getattr(f, 'id', None) is not None:
            all_faults_map[f.id] = f
    all_faults = list(all_faults_map.values())
    
    z_cache = {}
    for f in all_faults:
        f_id = f.id
        if f_id not in z_cache:
            try:
                z_cache[f_id] = set(s.id for s in f.interruption_location.all())
            except Exception:
                z_cache[f_id] = set()

    buckets = {}
    
    def add_to_bucket(f):
        if not getattr(f, 'is_fiber_fault', False) or not getattr(f, 'fault_occurrence_time', None):
            return
        a_id = getattr(f, 'interruption_location_a_id', None)
        if not a_id:
            return
        z_ids = z_cache.get(f.id, set())
        for z_id in z_ids:
            key = (a_id, z_id)
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(f)

    for f in all_faults:
        add_to_bucket(f)

    for key in buckets:
        unique_f = {}
        for f in buckets[key]:
            unique_f[f.id] = f
        buckets[key] = sorted(unique_f.values(), key=lambda x: x.fault_occurrence_time)

    kpi_repeat_ids = set()
    ui_repeat_ids = set()
    matched_preceding_faults = []

    SIXTY_DAYS_SECONDS = 60 * 86400

    for f in faults_list:
        if not getattr(f, 'is_fiber_fault', False) or not getattr(f, 'fault_occurrence_time', None):
            continue
        
        a_id = getattr(f, 'interruption_location_a_id', None)
        z_ids = z_cache.get(f.id, set())
        
        is_kpi = False
        is_ui = False
        f_time = f.fault_occurrence_time
        
        for z_id in z_ids:
            key = (a_id, z_id)
            if key not in buckets:
                continue
            
            bucket_faults = buckets[key]
            for pf in bucket_faults:
                if pf.id == f.id:
                    continue
                
                pf_time = pf.fault_occurrence_time
                diff_sec = (f_time - pf_time).total_seconds()
                
                # 若 pf_time 超过 f_time 60 天以上，后续的 pf_time 只会更晚，已不可能满足 <= 60 天
                if diff_sec < -SIXTY_DAYS_SECONDS:
                    break
                
                if 0 < diff_sec <= SIXTY_DAYS_SECONDS:
                    is_kpi = True
                
                if abs(diff_sec) <= SIXTY_DAYS_SECONDS:
                    is_ui = True
                    
                if is_kpi and is_ui:
                    break
            
            if is_kpi:
                kpi_repeat_ids.add(f.id)
            if is_ui:
                ui_repeat_ids.add(f.id)
            if is_kpi and is_ui:
                break

    matched_preceding_set = set()
    for pf in preceding_list:
        if not getattr(pf, 'is_fiber_fault', False) or not getattr(pf, 'fault_occurrence_time', None):
            continue
        
        a_id = getattr(pf, 'interruption_location_a_id', None)
        z_ids = z_cache.get(pf.id, set())
        
        matched = False
        pf_time = pf.fault_occurrence_time
        for z_id in z_ids:
            key = (a_id, z_id)
            if key not in buckets:
                continue
            
            bucket_faults = buckets[key]
            for cf in bucket_faults:
                # 使用 fault_ids_set O(1) 替代原本的 cf in faults_list O(N) 扫描
                if cf.id != pf.id and cf.id in fault_ids_set:
                    diff_sec = (cf.fault_occurrence_time - pf_time).total_seconds()
                    if diff_sec < -SIXTY_DAYS_SECONDS:
                        continue
                    if 0 < diff_sec <= SIXTY_DAYS_SECONDS:
                        matched = True
                        break
            if matched:
                break
        
        if matched:
            matched_preceding_set.add(pf.id)
            matched_preceding_faults.append(pf)

    return RepeatFaultResult(
        kpi_repeat_ids=kpi_repeat_ids,
        ui_repeat_ids=ui_repeat_ids,
        matched_preceding_faults=matched_preceding_faults
    )

