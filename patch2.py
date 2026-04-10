import re

file_path = 'd:/Src/netbox-otnfaults/netbox_otnfaults/tables.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'class OtnFaultImpactSummaryTable\(OtnFaultImpactTable\):\s*\"\"\"故障详情页关联业务的精简表格渲染\"\"\"\s*class Meta\(OtnFaultImpactTable\.Meta\):\s*fields = \([^)]+\)\s*default_columns = \([^)]+\)'

replacement = '''class OtnFaultImpactSummaryTable(OtnFaultImpactTable):
    \"\"\"故障详情页关联业务的精简表格渲染\"\"\"
    class Meta(OtnFaultImpactTable.Meta):
        fields = (
            'id', 'service_type', 'service_name',
            'service_interruption_time', 'service_recovery_time', 'service_duration',
            'secondary_faults', 'actions',
        )
        default_columns = (
            'id', 'service_type', 'service_name',
            'service_interruption_time', 'service_recovery_time', 'service_duration',
            'secondary_faults',
        )
        exclude = ('otn_fault', 'service_group', 'comments', 'tags', 'pk')'''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
