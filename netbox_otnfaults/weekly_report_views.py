"""
OTN 每周故障通报 - 后端视图与数据接口
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from datetime import datetime, timedelta, time
from collections import Counter

from .models import (
    OtnFault, OtnFaultImpact, ResourceTypeChoices, FaultCategoryChoices
)


class WeeklyReportPageView(PermissionRequiredMixin, View):
    """每周通报大屏页面视图 - 渲染全屏 HTML"""
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request):
        return render(request, 'netbox_otnfaults/weekly_report_dashboard.html')


class WeeklyReportDataAPI(PermissionRequiredMixin, View):
    """每周故障通报聚合数据 API"""
    permission_required = 'netbox_otnfaults.view_otnfault'

    def _get_fault_duration(self, f):
        if not f.fault_occurrence_time:
            return 0.0
        end_time = f.fault_recovery_time or timezone.now()
        return (end_time - f.fault_occurrence_time).total_seconds() / 3600.0

    def get(self, request) -> JsonResponse:
        now = timezone.localtime().date()
        
        # calculate period: last Saturday to last Friday
        days_since_friday = (now.weekday() - 4) % 7
        if days_since_friday == 0 and now.weekday() == 4:
            ed = now
        else:
            ed = now - timedelta(days=days_since_friday)
        st = ed - timedelta(days=6)
        
        st_dt = timezone.make_aware(datetime.combine(st, time.min))
        ed_dt = timezone.make_aware(datetime.combine(ed, time.max))
        prev_st_dt = st_dt - timedelta(days=7)
        prev_ed_dt = ed_dt - timedelta(days=7)

        # Query faults
        faults = OtnFault.objects.filter(
            fault_occurrence_time__range=(st_dt, ed_dt)
        ).select_related('province', 'interruption_location_a')
        
        prev_faults = OtnFault.objects.filter(
            fault_occurrence_time__range=(prev_st_dt, prev_ed_dt)
        )
        
        total_count = faults.count()
        prev_count = prev_faults.count()
        diff_count = total_count - prev_count
        
        self_built_count = faults.filter(resource_type=ResourceTypeChoices.SELF_BUILT).count()
        leased_count = faults.filter(resource_type__in=[ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED]).count()
        
        # Durations
        total_dur = sum(self._get_fault_duration(f) for f in faults)
        prev_dur = sum(self._get_fault_duration(f) for f in prev_faults)
        diff_dur = total_dur - prev_dur
        
        self_built_dur = sum(self._get_fault_duration(f) for f in faults if f.resource_type == ResourceTypeChoices.SELF_BUILT)
        leased_dur = sum(self._get_fault_duration(f) for f in faults if f.resource_type in [ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED])
        
        # Reasons analysis
        reasons_stats = {}
        for f in faults:
            if f.interruption_reason == 'cable_rectification' or f.fault_category == FaultCategoryChoices.FIBER_JITTER:
                continue
            
            r_txt = "未知原因"
            if f.interruption_reason:
                r_txt = f.get_interruption_reason_display()
            elif f.fault_category:
                r_txt = f.get_fault_category_display()
                
            reasons_stats[r_txt] = reasons_stats.get(r_txt, 0) + 1
            
        reason_chart_data = [{"name": k, "value": v} for k, v in reasons_stats.items()]
        # Sort descending
        reason_chart_data.sort(key=lambda x: x['value'], reverse=True)

        # Provinces (Top 3 or 4) processing
        province_counts = Counter()
        province_durs = Counter()
        for f in faults:
            prov_name = f.province.name if hasattr(f, 'province') and f.province else "未知"
            province_counts[prov_name] += 1
            province_durs[prov_name] += self._get_fault_duration(f)
            
        top_provinces = []
        for prov_name, count in province_counts.most_common(4):
            prov_faults = [f for f in faults if (f.province.name if f.province else "未知") == prov_name]
            p_reasons = Counter([f.get_interruption_reason_display() for f in prov_faults if f.interruption_reason])
            top_reason = p_reasons.most_common(1)[0][0] if p_reasons else "未知原因"
            
            paths = []
            for f in prov_faults:
                a_site = f.interruption_location_a.name if f.interruption_location_a else ""
                z_sites = [z.name for z in f.interruption_location.all()]
                z_site = z_sites[0] if z_sites else ""
                
                # shorten names
                a_site = a_site.replace("节点", "").replace("机房", "")
                z_site = z_site.replace("节点", "").replace("机房", "")
                
                if a_site and z_site:
                    paths.append(f"{a_site}-{z_site}")
                elif a_site:
                    paths.append(f"{a_site}")
            paths_txt = "、".join(list(set(paths))[:2])
            
            top_provinces.append({
                "province": prov_name,
                "count": count,
                "duration": round(province_durs[prov_name], 1),
                "main_reason": top_reason,
                "paths": paths_txt
            })

        # Major events > 8h
        long_faults = []
        no_const_dur = sum(self._get_fault_duration(f) for f in faults if f.interruption_reason != 'construction')
        
        for f in faults:
            if f.interruption_reason == 'construction':
                continue
            dur = self._get_fault_duration(f)
            if dur > 8.0:
                prov = f.province.name if f.province else "未知"
                loc_txt = f.fault_number or "未知编号"
                reason = f.get_interruption_reason_display() if f.interruption_reason else "未知"
                details = (f.fault_details or "").replace("\n", " ")[:30]
                long_faults.append({
                    "prov": prov,
                    "loc": loc_txt,
                    "duration": round(dur, 1),
                    "reason": reason,
                    "details": details
                })
                
        # Bare fiber impacts
        SERVICES = [
            "百度 昆汉广", "百度 京南昆", "百度 定保阳", "百度 杭州至苏州", "百度 北京至昆山",
            "华为 京汉广", "华为  贵广", "腾讯 上海至武汉", "腾讯 上海至深圳", "腾讯 上海至天津",
            "腾讯 北京至怀来", "阿里 杭州至河源", "阿里 广深河", "字节 上海至南通", "字节 国干二期",
            "字节 国干三期", "字节 蔚县至怀来", "字节 廊坊至怀来", "字节 灵丘至廊坊", 
            "创景万通 上海至深圳", "创景万通 津冀鲁", "硕富码", "快手 西安至太原", "快手 西安至郑州",
            "快手 西安至武汉", "信智通 石家庄至郑州、武汉至南京", "未来 东数西算"
        ]
        
        services_data = []
        for i, s_name in enumerate(SERVICES, 1):
            parts = [p.strip() for p in s_name.split(' ') if p.strip()]
            q = Q(service_type='bare_fiber') & Q(service_interruption_time__range=(st_dt, ed_dt))
            for p in parts:
                q &= Q(bare_fiber_service__name__icontains=p)
            
            impacts = OtnFaultImpact.objects.filter(q).select_related('otn_fault', 'otn_fault__province', 'otn_fault__interruption_location_a')
            
            if not impacts.exists():
                services_data.append({
                    "id": i, "name": s_name, "status": "no_interruption",
                    "break_cnt": 0, "block_cnt": 0, "jitter_cnt": 0, "duration": 0, "segments": ""
                })
                continue
                
            break_cnt = 0
            block_cnt = 0
            jitter_cnt = 0
            s_dur = 0.0
            segments = []
            
            for imp in impacts:
                f = imp.otn_fault
                if f.fault_category == FaultCategoryChoices.FIBER_JITTER:
                    jitter_cnt += 1
                else:
                    break_cnt += 1
                    block_cnt += 1
                    end_time = imp.service_recovery_time or timezone.now()
                    s_dur += (end_time - imp.service_interruption_time).total_seconds() / 3600.0
                    
                prov = f.province.name if f.province else ""
                loc = f.interruption_location_a.name.replace("节点", "").replace("机房", "") if f.interruption_location_a else ""
                rt = f.get_resource_type_display() if f.resource_type else ""
                reason = f.get_interruption_reason_display() if f.interruption_reason else (f.get_fault_category_display() if f.fault_category else "")
                
                seg = f"{prov}{loc[:4]}"
                if rt in ["租赁纤芯", "租赁"]: seg += "租赁"
                elif rt in ["自建光缆", "自建"]: seg += "自有"
                elif rt in ["协调资源", "协调"]: seg += "协调"
                
                if reason in ["线路整改", "割接"]: seg += "割接"
                elif reason: seg += f"{reason[:2]}"
                
                segments.append(seg)
                
            seg_txt = "、".join(list(set(segments)))
            
            status = "interruption"
            if break_cnt == 0 and jitter_cnt > 0:
                status = "jitter"
                
            services_data.append({
                "id": i, "name": s_name, "status": status,
                "break_cnt": break_cnt, "block_cnt": block_cnt, 
                "jitter_cnt": jitter_cnt, "duration": round(s_dur, 1), 
                "segments": seg_txt
            })

        return JsonResponse({
            "timestamp": now.isoformat(),
            "period": {
                "start": st_dt.strftime("%Y.%m.%d"),
                "end": ed_dt.strftime("%Y.%m.%d")
            },
            "summary": {
                "total_count": total_count,
                "diff_count": diff_count,
                "total_duration": round(total_dur, 1),
                "diff_duration": round(diff_dur, 1),
                "self_built": {"count": self_built_count, "duration": round(self_built_dur, 1)},
                "leased": {"count": leased_count, "duration": round(leased_dur, 1)},
                "no_const_duration": round(no_const_dur, 1)
            },
            "reasons_analysis": reason_chart_data,
            "top_provinces": top_provinces,
            "major_events": long_faults,
            "bare_fiber": services_data
        }, json_dumps_params={'ensure_ascii': False})
