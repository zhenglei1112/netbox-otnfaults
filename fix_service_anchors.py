import os

def fix_anchors(path, anchor_name):
    content = open(path, 'r', encoding='utf-8').read()
    
    # Add anchor to row div if not present
    div_start = '<div class="row mb-3">\n  <div class="col col-md-12">\n    <div class="card">\n      <h5 class="card-header'
    if div_start in content:
        content = content.replace(
            div_start,
            f'<div class="row mb-3" id="{anchor_name}">\n  <div class="col col-md-12">\n    <div class="card">\n      <h5 class="card-header'
        )
    
    # Filter links
    for f in ['all', 'this_week', 'this_month', 'this_year', 'last_7_days', 'last_30_days']:
        src = f'href="?time_filter={f}"'
        if src in content:
            content = content.replace(src, f'href="?time_filter={f}#{anchor_name}"')
            
    # Pagination arrows
    content = content.replace('&per_page={{ per_page }}">&lsaquo;', f'&per_page={{{{ per_page }}}}#{anchor_name}">&lsaquo;')
    content = content.replace('&per_page={{ per_page }}">&rsaquo;', f'&per_page={{{{ per_page }}}}#{anchor_name}">&rsaquo;')
    
    # Pagination numbers
    content = content.replace('&per_page={{ per_page }}">{{ num }}', f'&per_page={{{{ per_page }}}}#{anchor_name}">{{{{ num }}}}')
    
    # Per page dropdown
    for p in [25, 50, 100, 250, 500]:
        src = f'&per_page={p}"'
        if src in content:
            content = content.replace(src, f'&per_page={p}#{anchor_name}"')

    open(path, 'w', encoding='utf-8').write(content)

base = r'd:\Src\netbox-otnfaults\netbox_otnfaults\templates\netbox_otnfaults\\'
fix_anchors(base + 'barefiberservice.html', 'fault-impacts')
fix_anchors(base + 'circuitservice.html', 'fault-impacts')

print('Done')
