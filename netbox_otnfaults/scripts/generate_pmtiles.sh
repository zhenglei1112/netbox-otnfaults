#!/bin/bash
# =============================================================================
# PMTiles 生成脚本
# 将 GeoJSON 转换为 PMTiles 格式
# =============================================================================

INPUT_FILE="/opt/maps/data/otn_paths.geojson"
OUTPUT_FILE="/opt/maps/data/otn_paths.pmtiles"

# 检查输入文件
if [ ! -f "$INPUT_FILE" ]; then
    echo "错误: 输入文件 $INPUT_FILE 不存在"
    echo "请先运行 NetBox 脚本导出 GeoJSON"
    exit 1
fi

# 确保输出目录存在
mkdir -p "$(dirname "$OUTPUT_FILE")"

echo "开始生成 PMTiles..."
echo "输入: $INPUT_FILE"
echo "输出: $OUTPUT_FILE"

# 生成 PMTiles
tippecanoe \
    -o "$OUTPUT_FILE" \
    --force \
    -zg \
    --projection=EPSG:4326 \
    --drop-densest-as-needed \
    --extend-zooms-if-still-dropping \
    -l otn_paths \
    --name="OTN 光缆路径" \
    --description="NetBox OtnPath 数据导出" \
    "$INPUT_FILE"

if [ $? -eq 0 ]; then
    echo "PMTiles 生成成功!"
    echo "文件大小: $(ls -lh "$OUTPUT_FILE" | awk '{print $5}')"
else
    echo "PMTiles 生成失败!"
    exit 1
fi
