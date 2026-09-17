"""Summarize one or more browser diagnostic exports; never contacts a server."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from statistics import median
from typing import Any


def summarize(reports: list[dict[str, Any]]) -> str:
    requests: dict[str, list[dict]] = defaultdict(list)
    renders: dict[str, list[float]] = defaultdict(list)
    stages: dict[str, list[dict]] = defaultdict(list)
    findings: list[dict] = []
    for report in reports:
        findings.extend(report.get('findings', []))
        for row in report.get('records', []):
            if row['type'] == 'request':
                server = row.get('server') or {}
                dimensions = json.dumps(row.get('parameters', {}), ensure_ascii=False, sort_keys=True)
                key = f"{row.get('action', 'unknown')} | {row['endpoint']} | {dimensions} | {server.get('cache', 'no backend data')}"
                requests[key].append(row)
                for stage in server.get('stages', []):
                    stages[stage['name']].append(stage)
            elif row['type'] == 'render':
                renders[row['name']].append(row['ms'])
    output = ['# 故障统计性能实测汇总', '', '请求耗时为请求发起至 JSON 读取完成，含网络和解析；阶段为后端计时。失败/未完成请求不计入分位数。', '', '| 交互 / 接口 / 范围 / 缓存 | 请求数 | 完成数 | 中位数 ms | P95 ms | 最大 SQL 数 |', '|---|---:|---:|---:|---:|---:|']
    for key, rows in requests.items():
        times = sorted(row['complete_ms'] for row in rows if 'complete_ms' in row and not row.get('error'))
        mid = f'{median(times):.2f}' if times else '-'
        p95 = f'{times[math.ceil(len(times) * .95) - 1]:.2f}' if times else '-'
        sql_counts = [row['server']['sql_count'] for row in rows if row.get('server')]
        sql = max(sql_counts) if sql_counts else '-'
        output.append(f"| {key.replace('|', '/')} | {len(rows)} | {len(times)} | {mid} | {p95} | {sql} |")
    output.extend(['', '## 后端自身耗时 Top 15', '', '| 阶段 | 样本数 | 平均自身 ms | 平均含子调用 ms |', '|---|---:|---:|---:|'])
    ordered = sorted(stages.items(), key=lambda pair: sum(row.get('self_ms', 0) for row in pair[1]) / len(pair[1]), reverse=True)
    for name, rows in ordered[:15]:
        output.append(f"| {name} | {len(rows)} | {sum(row.get('self_ms', 0) for row in rows)/len(rows):.2f} | {sum(row['ms'] for row in rows)/len(rows):.2f} |")
    output.extend(['', '## 前端同步渲染 Top 15', ''])
    for name, times in sorted(renders.items(), key=lambda pair: max(pair[1]), reverse=True)[:15]:
        output.append(f'- {name}: 最大 {max(times):.2f} ms，中位数 {median(times):.2f} ms，{len(times)} 次')
    output.extend(['', '## 自动提示（排查线索，不等于已确认根因）', ''])
    output.extend('- ' + json.dumps(item, ensure_ascii=False) for item in findings)
    if not findings:
        output.append('- 未触发阈值；仍需比较请求重复率和阶段耗时。')
    return '\n'.join(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', nargs='+', type=Path)
    args = parser.parse_args()
    print(summarize([json.loads(path.read_text(encoding='utf-8')) for path in args.reports]))


if __name__ == '__main__':
    main()
