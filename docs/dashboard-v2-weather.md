# V2 免费气象图层

## 部署方配置（本功能不自动安装定时任务）

安装插件依赖，包括 `requests` 和 `defusedxml`。在 NetBox 的插件配置中补充：

```python
PLUGINS_CONFIG = {
    'netbox_otnfaults': {
        # 替换为真实的应用标识和维护人联系信息，不要原样使用示例。
        'dashboard_v2_weather_user_agent': 'YourCompany-NetBox/1.0 (weather-admin@your-company.example)',
        'dashboard_v2_weather_thresholds': {
            'rain': 10.0,  # 一小时累计降雨 mm
            'wind': 10.0,  # 风速 m/s
            'heat': 35.0,  # 摄氏度
            'cold': 0.0,
        },
    },
}
```

保留已有插件配置，不要覆盖其他字段。阈值应为有限数值；这是内部模型风险提示，不是官方预警等级。

使用与 NetBox 相同环境、配置及共享 Redis 缓存运行：

```sh
python manage.py sync_dashboard_weather
```

部署方可配置每10分钟运行一次。不要在每个 Web worker 中运行，也不要使用进程内 LocMemCache：同步进程和 Web 进程必须共享缓存。命令有同步锁；MET 查询以半秒最小间隔串行请求，相邻站点按两位小数坐标合并，并遵守上游缓存时间、条件请求和429退避。大量站点初次同步可能较慢；50分钟工作预算后留待后续批次继续，已成功采样缓存可复用。

缺少真实 User-Agent 联系信息时 MET 不发请求，HKO 仍独立同步。首个成功同步前气象模块显示加载中；异常显示于右上角，不影响故障数据刷新。30分钟没有同步检查标记为过期；超过24小时的模型／台风报告不再绘制。前端读取气象缓存的周期为30秒。

服务器须能通过 HTTPS 访问 `api.met.no`、`www.weather.gov.hk`、`www.hko.gov.hk`，并具备有效 CA 根证书。程序不关闭证书校验、不跟随重定向、不请求任意台风 URL。来源字段或域名变更应人工核实后适配。

## 数据与显示边界

- `dashboard-v2/weather/` 需具备 V2 查看权限，站点按 `Site.objects.restrict(user, 'view')` 过滤；不向外部发送站点名称、编号或业务信息，只发送舍入后的坐标。
- MET Norway 为全球模型预报；未来24小时满足阈值的站点显示雨滴、风、温度图标，低缩放聚合。光晕是屏幕装饰，不是天气区域。
- HKO XML 提供过去、当前、预测位置和强度。来源未提供真实风圈，不绘制风圈；无时间插值点仅参与绘线。
- 不改变故障／割接／重保列表、指示线布局或巡播队列。电脑悬停可读详情；大屏不弹文字框。
- 两个图层独立开关，默认开启；本地存储不可用时使用会话状态。Debug 数据模拟同时切换气象模拟，不混入真实数据。
- 地图底部保留来源署名。预测位置与强度可能存在偏差，不能据此断言业务已中断或站点必然受灾。

## 免费来源

- MET Norway API：https://api.met.no/weatherapi/locationforecast/2.0/documentation
- MET Norway 许可：https://api.met.no/doc/License （默认 CC BY 4.0 / NLOD 2.0）
- MET Norway 访问要求：https://api.met.no/doc/TermsOfService
- 香港天文台数据：https://data.gov.hk/en-data/dataset/hk-hko-rss-tc-track-info
- 数据字典：https://www.weather.gov.hk/wxinfo/currwx/HKO_TCTrackInfo_DataDictionary_en.pdf
- DATA.GOV.HK 使用条款：https://data.gov.hk/en/terms-and-conditions

免费数据没有可用性保证。上游不可用时不自动切换付费渠道，不将失败解释为无风险。
