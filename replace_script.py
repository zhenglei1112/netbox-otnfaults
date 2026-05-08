import sys
import re

path = r'd:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js'
with open(path, 'r', encoding='utf8') as f:
    code = f.read()

# 1. resourceData
code = code.replace(
    'const resourceData = chartsData.resource\n            .map(item => ({name: item.name, value: item.value, _duration: item.duration}))\n            .sort((a, b) => (resourceTypeRank.get(a.name) ?? resourceTypeOrder.length) - (resourceTypeRank.get(b.name) ?? resourceTypeOrder.length));',
    'const isResourceCount = currentMetricResource === \'count\';\n        const resourceData = chartsData.resource\n            .map(item => ({name: item.name, value: isResourceCount ? item.value : item.duration, _duration: item.duration, _count: item.value}))\n            .sort((a, b) => (resourceTypeRank.get(a.name) ?? resourceTypeOrder.length) - (resourceTypeRank.get(b.name) ?? resourceTypeOrder.length));'
)
code = code.replace(
    'return `${params.name}\\n${params.value}次 ${percent}%`;',
    'return isResourceCount ? `${params.name}\\n${item._count}次 ${percent}%` : `${params.name}\\n${item._duration.toFixed(2)}小时 ${percent}%`;'
)
code = code.replace(
    'let avg = p.value > 0 ? (p.data._duration / p.value).toFixed(2) : "0.00";\n                    return `${p.marker || \'\'}${p.name}: ${p.value}次 (${percent}%)<br/>` +\n                           `<span style="margin-left:14px;">总历时: ${p.data._duration} 小时</span><br/>` +\n                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;',
    'let avg = p.data._count > 0 ? (p.data._duration / p.data._count).toFixed(2) : "0.00";\n                    return `${p.marker || \'\'}${p.name}: ${p.data._count}次 (${isResourceCount ? percent + \'%\' : \'-\'})<br/>` +\n                           `<span style="margin-left:14px;">总历时: ${p.data._duration} 小时 (${!isResourceCount ? percent + \'%\' : \'-\'})</span><br/>` +\n                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;'
)
code = code.replace(
    'data: resourceData.map(item => ({value: item.value, _duration: item._duration, itemStyle: { color: resourceColorMap[item.name] || chartTheme.primary }}))',
    'data: resourceData.map(item => ({value: item.value, _duration: item._duration, _count: item._count, itemStyle: { color: resourceColorMap[item.name] || chartTheme.primary }}))'
)

# 2. provinceData
code = code.replace(
    'let provData = chartsData.province;',
    'const isProvinceCount = currentMetricProvince === \'count\';\n        let provData = chartsData.province;'
)
code = code.replace(
    'data: provData.map(item => ({value: item.value, _duration: item.duration}))',
    'data: provData.map(item => ({value: isProvinceCount ? item.value : item.duration, _duration: item.duration, _count: item.value}))'
)
code = code.replace(
    'label: { show: true, position: \'top\', color: chartTheme.heading, fontWeight: 600 },',
    'label: { \n                    show: true, position: \'top\', color: chartTheme.heading, fontWeight: 600,\n                    formatter: function(params) { return isProvinceCount ? (params.value > 0 ? params.value : \'\') : (params.value > 0 ? params.value.toFixed(1) : \'\'); }\n                },'
)
code = code.replace(
    'let avg = p.value > 0 ? (p.data._duration / p.value).toFixed(2) : "0.00";\n                    return `${p.marker || \'\'}${p.name}: ${p.value}次<br/>` +\n                           `<span style="margin-left:14px;">总历时: ${p.data._duration} 小时</span><br/>` +\n                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;',
    'let avg = p.data._count > 0 ? (p.data._duration / p.data._count).toFixed(2) : "0.00";\n                    return `${p.marker || \'\'}${p.name}: ${p.data._count}次<br/>` +\n                           `<span style="margin-left:14px;">总历时: ${p.data._duration} 小时</span><br/>` +\n                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;'
)

# 3. reasonData
code = code.replace(
    'const reasonData = chartsData.reason.map(item => ({name: item.name, value: item.value, _duration: item.duration}));',
    'const isReasonCount = currentMetricReason === \'count\';\n        const reasonData = chartsData.reason.map(item => ({name: item.name, value: isReasonCount ? item.value : item.duration, _duration: item.duration, _count: item.value}));'
)
code = code.replace(
    'formatter: name => formatLegendMetricLabel(name, reasonLegendByName, reasonTotal),',
    'formatter: name => {\n                    const item = reasonLegendByName.get(name);\n                    if (!item) return name;\n                    const percent = reasonTotal > 0 ? ((item.value / reasonTotal) * 100).toFixed(2) : "0.00";\n                    return isReasonCount ? `${name}  ${item._count}次 ${percent}%` : `${name}  ${item._duration.toFixed(2)}时 ${percent}%`;\n                },'
)
code = code.replace(
    'let avg = params.value > 0 ? (params.data._duration / params.value).toFixed(2) : "0.00";\n                    return `${params.marker}${params.name}: ${params.value}次 (${params.percent}%)<br/>` +\n                           `<span style="margin-left:14px;">总历时: ${params.data._duration} 小时</span><br/>` +\n                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;',
    'let avg = params.data._count > 0 ? (params.data._duration / params.data._count).toFixed(2) : "0.00";\n                    return `${params.marker}${params.name}: ${params.data._count}次 (${isReasonCount ? params.percent + \'%\' : \'-\'})<br/>` +\n                           `<span style="margin-left:14px;">总历时: ${params.data._duration} 小时 (${!isReasonCount ? params.percent + \'%\' : \'-\'})</span><br/>` +\n                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;'
)

with open(path, 'w', encoding='utf8') as f:
    f.write(code)

print("Replacement done!")
