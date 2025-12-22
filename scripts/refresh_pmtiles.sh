#!/bin/bash
# =============================================================================
# 一键刷新 PMTiles
# 整合 GeoJSON 导出和 PMTiles 生成流程
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NETBOX_DIR="/opt/netbox"

echo "=========================================="
echo " OtnPath PMTiles 刷新脚本"
echo "=========================================="

# 步骤 1: 导出 GeoJSON
echo ""
echo "[步骤 1/2] 调用 NetBox 脚本导出 GeoJSON..."
cd "$NETBOX_DIR"
source "$NETBOX_DIR/venv/bin/activate"

python manage.py runscript netbox_otnfaults.scripts.export_paths_geojson --commit

if [ $? -ne 0 ]; then
    echo "GeoJSON 导出失败!"
    exit 1
fi

# 步骤 2: 生成 PMTiles
echo ""
echo "[步骤 2/2] 生成 PMTiles..."
"$SCRIPT_DIR/generate_pmtiles.sh"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo " 刷新完成!"
    echo "=========================================="
else
    echo "PMTiles 生成失败!"
    exit 1
fi
