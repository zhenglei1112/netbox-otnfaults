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

    all_faults = faults_list + past_list + preceding_list
    
    z_cache = {}
    for f in all_faults:
        if f.id not in z_cache:
            z_cache[f.id] = set(s.id for s in f.interruption_location.all())

    buckets = {}
    
    def add_to_bucket(f):
        if not f.is_fiber_fault or not f.fault_occurrence_time:
            return
        a_id = f.interruption_location_a_id
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

    for f in faults_list:
        if not f.is_fiber_fault or not f.fault_occurrence_time:
            continue
        
        a_id = f.interruption_location_a_id
        z_ids = z_cache.get(f.id, set())
        
        is_kpi = False
        is_ui = False
        
        for z_id in z_ids:
            key = (a_id, z_id)
            if key not in buckets:
                continue
            
            bucket_faults = buckets[key]
            f_time = f.fault_occurrence_time
            
            for pf in bucket_faults:
                if pf.id == f.id:
                    continue
                
                pf_time = pf.fault_occurrence_time
                time_diff = f_time - pf_time
                
                if 0 < time_diff.total_seconds() <= 60 * 86400:
                    is_kpi = True
                
                if abs(time_diff.total_seconds()) <= 60 * 86400:
                    is_ui = True
                    
                if is_kpi and is_ui:
                    break
            
            if is_kpi:
                kpi_repeat_ids.add(f.id)
            if is_ui:
                ui_repeat_ids.add(f.id)

    matched_preceding_set = set()
    for pf in preceding_list:
        if not pf.is_fiber_fault or not pf.fault_occurrence_time:
            continue
        
        a_id = pf.interruption_location_a_id
        z_ids = z_cache.get(pf.id, set())
        
        matched = False
        for z_id in z_ids:
            key = (a_id, z_id)
            if key not in buckets:
                continue
            
            bucket_faults = buckets[key]
            pf_time = pf.fault_occurrence_time
            
            for cf in bucket_faults:
                if cf.id != pf.id and cf in faults_list:
                    time_diff = cf.fault_occurrence_time - pf_time
                    if 0 < time_diff.total_seconds() <= 60 * 86400:
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
