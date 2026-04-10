import re
with open('templates/netbox_otnfaults/circuitservice.html', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('<th scope="row">带宽</th>', '<th scope="row">带宽(Mbps)</th>')
content = re.sub(r'{%\s*with\s+color=object.get_bandwidth_color\s*%}.*?{%\s*endwith\s*%}', '{{ object.bandwidth }}', content, flags=re.DOTALL)
with open('templates/netbox_otnfaults/circuitservice.html', 'w', encoding='utf-8') as f:
    f.write(content)
