"""
NetBox 自定义脚本：导出 OtnPath 为 GeoJSON
用于生成 PMTiles 的数据源
"""
from extras.scripts import Script, StringVar
from netbox_otnfaults.models import OtnPath
import json
import os


class ExportPathsGeoJSON(Script):
    class Meta:
        name = "导出路径为 GeoJSON"
        description = "将所有 OtnPath 导出为 GeoJSON 文件，供 tippecanoe 生成 PMTiles"

    output_path = StringVar(
        description="GeoJSON 输出路径",
        default="/opt/maps/data/otn_paths.geojson"
    )

    def run(self, data, commit):
        output_file = data.get('output_path', '/opt/maps/data/otn_paths.geojson')
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                self.log_info(f"已创建目录: {output_dir}")
            except Exception as e:
                self.log_failure(f"无法创建目录 {output_dir}: {str(e)}")
                return

        features = []
        skipped = 0
        
        for path in OtnPath.objects.all():
            # 跳过没有几何数据的路径
            if not path.geometry:
                skipped += 1
                continue
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": path.geometry
                },
                "properties": {
                    "id": path.pk,
                    "name": path.name,
                    "site_a": path.site_a.name if path.site_a else None,
                    "site_z": path.site_z.name if path.site_z else None,
                    "site_a_id": path.site_a.pk if path.site_a else None,
                    "site_z_id": path.site_z.pk if path.site_z else None,
                    "cable_type": path.cable_type,
                    "length_m": float(path.calculated_length) if path.calculated_length else None,
                    "description": path.description or ""
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(geojson, f, ensure_ascii=False, indent=2)
            
            self.log_success(f"已导出 {len(features)} 条路径到 {output_file}")
            if skipped > 0:
                self.log_warning(f"跳过 {skipped} 条无几何数据的路径")
        except Exception as e:
            self.log_failure(f"写入文件失败: {str(e)}")
