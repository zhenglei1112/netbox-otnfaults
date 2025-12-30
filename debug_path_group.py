import os
import django
import sys

# 设置 Django 环境
# 假设 manage.py 在 d:\Src\netbox-otnfaults\manage.py，需要将项目根目录添加到 python path
sys.path.append(r'd:\Src\netbox-otnfaults')
# netbox 通常需要设置 DJANGO_SETTINGS_MODULE，这里假设是 netbox.settings
# 或者尝试加载 setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
django.setup()

from netbox_otnfaults.models import OtnPathGroup

try:
    print("Testing OtnPathGroup(id=1)...")
    path_group = OtnPathGroup.objects.get(pk=1)
    print(f"PathGroup: {path_group.name}")
    
    paths_with_geom = path_group.paths.exclude(geometry__isnull=True).exclude(geometry=[])
    print(f"Total paths with geometry: {paths_with_geom.count()}")

    for path in paths_with_geom:
        print(f"Processing path: {path.pk} - {path.name}")
        geom = path.geometry
        if isinstance(geom, list):
            coords = geom
            print(f"  Type: List, Points: {len(coords)}")
        else:
            coords = geom.get('coordinates', [])
            print(f"  Type: GeoJSON, Points: {len(coords)}")
        
    print("Test completed successfully.")

except Exception as e:
    print(f"Error occurred: {e}")
