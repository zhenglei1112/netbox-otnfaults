import sys
from io import StringIO
from django.utils import timezone
from datetime import timedelta, datetime, time
from django.db.models import Count, Q
from decimal import Decimal
from collections import Counter

from extras.scripts import Script, DateVar
from netbox_otnfaults.models import OtnFault, OtnFaultImpact, ResourceTypeChoices, FaultCategoryChoices


class WeeklyReportText(Script):
    class Meta:
        name = "每周故障通报(文本格式)"
        description = "自动提取上周六至本周五的故障，按特定的行政通报文档格式输出。"
        commit_default = False

    start_date = DateVar(label="统计周期开始 (默认最近的周六)", required=False)
    end_date = DateVar(label="统计周期结束 (默认最近的周五)", required=False)

    def calculate_dates(self, user_start, user_end):
        now = timezone.localtime().date()
        if user_start and user_end:
            st = user_start
            ed = user_end
        else:
            # find most recent Friday (weekday=4)
            days_since_friday = (now.weekday() - 4) % 7
            if days_since_friday == 0 and now.weekday() == 4:
                ed = now
            else:
                ed = now - timedelta(days=days_since_friday)
            st = ed - timedelta(days=6) # 6 days before Friday is Saturday
        
        # current period borders (local time based to aware)
        st_dt = timezone.make_aware(datetime.combine(st, time.min))
        ed_dt = timezone.make_aware(datetime.combine(ed, time.max))
        # prev period borders
        prev_st_dt = st_dt - timedelta(days=7)
        prev_ed_dt = ed_dt - timedelta(days=7)
        
        return st, ed, st_dt, ed_dt, prev_st_dt, prev_ed_dt

    def get_fault_duration(self, f):
        if not f.fault_occurrence_time:
            return 0.0
        end_time = f.fault_recovery_time or timezone.now()
        return (end_time - f.fault_occurrence_time).total_seconds() / 3600.0

    def run(self, data, commit):
        user_st = data.get('start_date')
        user_ed = data.get('end_date')
        
        st, ed, st_dt, ed_dt, prev_st_dt, prev_ed_dt = self.calculate_dates(user_st, user_ed)
        self.log_info(f"统计周期: {st_dt} - {ed_dt}")
        
        # Query faults
        faults = OtnFault.objects.filter(fault_occurrence_time__range=(st_dt, ed_dt)).select_related('province', 'interruption_location_a')
        prev_faults = OtnFault.objects.filter(fault_occurrence_time__range=(prev_st_dt, prev_ed_dt))
        
        total_count = faults.count()
        prev_count = prev_faults.count()
        diff_count = total_count - prev_count
        diff_count_str = f"增加{diff_count}" if diff_count >= 0 else f"减少{abs(diff_count)}"
        
        self_built_count = faults.filter(resource_type=ResourceTypeChoices.SELF_BUILT).count()
        leased_count = faults.filter(resource_type__in=[ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED]).count()
        
        # Reason counts
        construction_count = faults.filter(interruption_reason='construction').count()
        cable_rect_count = faults.filter(interruption_reason='cable_rectification').count()
        degradation_count = faults.filter(fault_category=FaultCategoryChoices.FIBER_DEGRADATION).count()
        unknown_count = faults.filter(interruption_reason='unknown').count()
        natural_disaster_count = faults.filter(interruption_reason='natural_disaster').count()
        traffic_accident_count = faults.filter(interruption_reason='traffic_accident').count()
        
        # pigtail needs to check location and recovery mode
        pigtail_count = faults.filter(Q(cable_break_location='pigtail') | Q(recovery_mode='tail_fiber_replacement')).count()
        animal_damage_count = faults.filter(interruption_reason='animal_damage').count()
        jitter_count = faults.filter(fault_category=FaultCategoryChoices.FIBER_JITTER).count()
        
        # Top reasons excluding cable_rectification and jitter
        reason_display_list = []
        for f in faults:
            if f.interruption_reason == 'cable_rectification' or f.fault_category == FaultCategoryChoices.FIBER_JITTER:
                continue
            if f.interruption_reason:
                r_txt = f.get_interruption_reason_display()
            elif f.fault_category:
                r_txt = f.get_fault_category_display()
            else:
                r_txt = "未知"
            reason_display_list.append(r_txt)
            
        counter = Counter(reason_display_list)
        top_reasons_items = counter.most_common(3)
        top_reasons = "、".join([item[0] for item in top_reasons_items]) if top_reasons_items else "未知"
        
        # Durations
        total_dur = sum(self.get_fault_duration(f) for f in faults)
        prev_dur = sum(self.get_fault_duration(f) for f in prev_faults)
        diff_dur = total_dur - prev_dur
        diff_dur_str = f"增加{diff_dur:.1f}" if diff_dur >= 0 else f"减少{abs(diff_dur):.1f}"
        
        self_built_dur = sum(self.get_fault_duration(f) for f in faults if f.resource_type == ResourceTypeChoices.SELF_BUILT)
        leased_dur = sum(self.get_fault_duration(f) for f in faults if f.resource_type in [ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED])
        no_const_dur = sum(self.get_fault_duration(f) for f in faults if f.interruption_reason != 'construction')
        
        # Provinces
        province_counts = Counter()
        province_durs = Counter()
        for f in faults:
            prov_name = f.province.name if hasattr(f, 'province') and f.province else "未知"
            # 排除'未知'省份以获得更有意义的排行，如果只有未知则保留
            province_counts[prov_name] += 1
            province_durs[prov_name] += self.get_fault_duration(f)
            
        top_prov_count_str = "无"
        if province_counts:
            top_p_c = province_counts.most_common(1)[0][0]
            count_p_c = province_counts[top_p_c]
            
            p_faults = [f for f in faults if (f.province.name if f.province else "未知") == top_p_c]
            p_reasons = Counter([f.get_interruption_reason_display() for f in p_faults if f.interruption_reason])
            top_p_reason = p_reasons.most_common(1)[0][0] if p_reasons else "未知"
            
            paths = []
            for f in p_faults:
                a_site = f.interruption_location_a.name if f.interruption_location_a else ""
                z_sites = [z.name for z in f.interruption_location.all()]
                z_site = z_sites[0] if z_sites else ""
                if a_site and z_site:
                    paths.append(f"{a_site}至{z_site}段")
                elif a_site:
                    paths.append(f"{a_site}段")
            paths_txt = "、".join(list(set(paths))[:2])
            top_prov_count_str = f"{top_p_c}{count_p_c}次（{top_p_reason}原因为主，{paths_txt}）；"

        top_prov_dur_str = "无"
        if province_durs:
            top_p_d = province_durs.most_common(1)[0][0]
            dur_p_d = province_durs[top_p_d]
            
            p_faults_d = [f for f in faults if (f.province.name if f.province else "未知") == top_p_d]
            p_reasons_d = Counter([f.get_interruption_reason_display() for f in p_faults_d if f.interruption_reason])
            top_pd_reason = p_reasons_d.most_common(1)[0][0] if p_reasons_d else "未知"
            
            paths_d = []
            for f in p_faults_d:
                a_site = f.interruption_location_a.name if f.interruption_location_a else ""
                z_sites = [z.name for z in f.interruption_location.all()]
                z_site = z_sites[0] if z_sites else ""
                if a_site and z_site:
                    paths_d.append(f"{a_site}-{z_site}")
                elif a_site:
                    paths_d.append(a_site)
            pathd_txt = "、".join(list(set(paths_d))[:2])
            top_prov_dur_str = f"{top_p_d}累计中断{dur_p_d:.1f}小时（{pathd_txt}{top_pd_reason}）；"
            
        # Single interruptions > 8h
        long_faults = []
        for f in faults:
            if f.interruption_reason == 'construction':
                continue
            dur = self.get_fault_duration(f)
            if dur > 8.0:
                prov = f.province.name if f.province else "未知"
                a_site = f.interruption_location_a.name if f.interruption_location_a else ""
                z_sites = [z.name for z in f.interruption_location.all()]
                z_site = z_sites[0] if z_sites else ""
                reason = f.get_interruption_reason_display() if f.interruption_reason else "未知"
                details = (f.fault_details or "").replace("\n", " ")[:40]
                loc_txt = f"{a_site}-{z_site}" if z_site else a_site
                long_faults.append(f"{prov} {loc_txt}，中断{dur:.1f}小时，{reason}导致，{details}；")
        long_faults_str = "\n".join(long_faults) if long_faults else "无；"
        
        # 裸纤业务
        SERVICES = [
            "百度 昆汉广", "百度 京南昆", "百度 定保阳", "百度 杭州至苏州", "百度 北京至昆山",
            "华为 京汉广", "华为  贵广", "腾讯 上海至武汉", "腾讯 上海至深圳", "腾讯 上海至天津",
            "腾讯 北京至怀来", "阿里 杭州至河源", "阿里 广深河", "字节 上海至南通", "字节 国干二期",
            "字节 国干三期", "字节 蔚县至怀来", "字节 廊坊至怀来", "字节 灵丘至廊坊", 
            "创景万通 上海至深圳", "创景万通 津冀鲁", "硕富码", "快手 西安至太原", "快手 西安至郑州",
            "快手 西安至武汉", "信智通 石家庄至郑州、武汉至南京", "未来 东数西算"
        ]
        
        table_rows = []
        for i, s_name in enumerate(SERVICES, 1):
            parts = [p.strip() for p in s_name.split(' ') if p.strip()]
            q = Q(service_type='bare_fiber') & Q(service_interruption_time__range=(st_dt, ed_dt))
            for p in parts:
                q &= Q(bare_fiber_service__name__icontains=p)
            
            impacts = OtnFaultImpact.objects.filter(q).select_related('otn_fault', 'otn_fault__province', 'otn_fault__interruption_location_a')
            
            if not impacts.exists():
                table_rows.append(f"| {i} | {s_name} | 没有中断 | - | 0 | - | - |")
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
                
                # 山东兴隆租赁割接 这种格式
                seg = f"{prov}{loc[:4]}"
                if rt == "租赁纤芯" or rt == "租赁": seg += "租赁"
                elif rt == "自建光缆" or rt == "自建": seg += "自有"
                elif rt == "协调资源" or rt == "协调": seg += "协调"
                
                if reason == "线路整改" or reason == "割接": seg += "割接"
                elif reason: seg += f"{reason[:2]}"
                
                segments.append(seg)
                
            seg_txt = "、".join(list(set(segments)))
            
            if break_cnt > 0 and jitter_cnt > 0:
                cb_txt = f"光缆中断{break_cnt}次<br>抖动{jitter_cnt}次"
                # Table column limits, user wants "断x次", "阻断x次", "抖动x次"...
                c1 = f"光缆中断{break_cnt}次"
                c2 = f"造成业务阻断{block_cnt}次"
                c3 = f"抖动{jitter_cnt}次"
                c4 = f"阻断{s_dur:.1f}小时"
            elif break_cnt > 0:
                c1 = f"光缆中断{break_cnt}次"
                c2 = f"造成业务阻断{block_cnt}次"
                c3 = "-"
                c4 = f"阻断{s_dur:.1f}小时"
            elif jitter_cnt > 0:
                c1 = "-"
                c2 = "-"
                c3 = f"抖动{jitter_cnt}次"
                c4 = "-"
            else:
                c1 = "没有中断"
                c2 = "-"
                c3 = "0"
                c4 = "-"
                
            table_rows.append(f"| {i} | {s_name} | {c1} | {c2} | {c3} | {c4} | {seg_txt} |")
            
        md_table = "\n".join([
            "| 序号 | 项目名称 | 光缆中断次数 | 业务阻断次数 | 抖动次数 | 业务阻断历时 | 重点故障段 |",
            "|---|---|---|---|---|---|---|",
        ] + table_rows)
        
        # Build Report Text
        t_start = st_dt.strftime("%Y年%m月%d日")
        t_end = ed_dt.strftime("%Y年%m月%d日")
        w_start = "周六"
        w_end = "周五"
        
        report = []
        report.append(f"**{t_start}（{w_start}）-{t_end}（{w_end}）**")
        report.append("")
        
        report.append(
            f"通报一下上周光缆中断情况，上周处理光纤故障共{total_count}次，比上上周{diff_count_str}次，"
            f"其中自建光缆中断{self_built_count}次，协调和租赁纤芯中断{leased_count}次，"
            f"中断原因以：{top_reasons}为主。（去除割接报备、线路抖动前三故障原因）"
        )
        report.append("")
        
        report.append(
            f"（道路施工{construction_count}次、线路整改{cable_rect_count}次（_次满足24小时前报备，_次未满足24小时前报备）、"
            f"自然劣化{degradation_count}次、无法查明{unknown_count}次、自然灾害{natural_disaster_count}次、"
            f"交通事故{traffic_accident_count}次、尾纤损坏{pigtail_count}次、动物破坏{animal_damage_count}次、"
            f"线路抖动{jitter_count}次）。"
        )
        report.append("")
        
        report.append(
            f"中断总时长{total_dur:.1f}小时，比上上周{diff_dur_str}小时，"
            f"其中自建光缆中断{self_built_dur:.1f}小时，协调和租赁纤芯中断{leased_dur:.1f}小时，"
            f"不含道路施工引起的中断总时长{no_const_dur:.1f}小时。"
        )
        report.append("")
        
        report.append("中断次数较多的省份：")
        report.append(top_prov_count_str)
        report.append("")
        
        report.append("中断总时长较长的省份：")
        report.append(top_prov_dur_str)
        report.append("")
        
        report.append("不含道路施工，单次中断超过8小时的有：")
        report.append(long_faults_str)
        report.append("")
        
        report.append("裸纤业务线路中断情况：")
        report.append(md_table)
        
        full_text = "\n".join(report)
        self.log_info("------------- 报告内容 -------------")
        for line in report:
            self.log_info(line)
            
        return full_text
