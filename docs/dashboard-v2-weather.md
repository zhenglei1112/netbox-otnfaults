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

部署方可配置每10分钟运行一次。不要在每个 Web worker 中运行，也不要使用进程内 LocMemCache：同步进程和 Web 进程必须共享缓存。命令有同步锁；MET 按 `Site.region` 分组，在每组有有效坐标的站点中选择最接近组内坐标均值的代表点，坐标保留两位小数；未配置区域或有效坐标的站点不能获得对应采样。查询以半秒最小间隔串行请求，并遵守上游缓存时间、条件请求和429退避。50分钟工作预算后留待后续批次继续，已成功采样缓存可复用。

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

## 192.168.30.176 基础部署记录（2026-09-17）

服务器为 Ubuntu 24.04.4、NetBox 4.4.2，使用原生 systemd 部署；`/opt/netbox` 指向 `/opt/netbox-4.4.2`，应用用户为 `netbox`。已安装 `requests 2.32.5`、`defusedxml 0.7.1`，缓存后端为 `django_redis.cache.RedisCache`，系统时间已同步。

此次仅补齐当前已安装插件中的 `services/dashboard_weather.py`、`services/weather_geometry.py` 和 `management/commands/sync_dashboard_weather.py`，来源为本仓库 `ca92f554a19f19a71cdc875b67fb00eb8609ad68` 工作区。没有替换整个插件、修改 NetBox 核心配置、执行数据库迁移或重启 Web 服务。完整大屏代码仍由后续发布流程更新。

### 已安装文件

| 文件/目录 | 用途 |
| --- | --- |
| `/opt/netbox-weather/sync.py` | 使用应用虚拟环境与配置同步，来源失败返回非零退出码 |
| `/etc/netbox-dashboard-weather.env` | 维护联系信息及 NetBox 项目路径，root 所有、权限 0600 |
| `/etc/systemd/system/netbox-dashboard-weather.service` | 以 netbox 用户运行的 oneshot 服务，超时 65 分钟，日志进入 journal |
| `/etc/systemd/system/netbox-dashboard-weather.timer` | 每小时第 0/10/20/30/40/50 分钟触发，最多随机延迟 20 秒，开机启用并补触发错过的计划 |
| `/var/backups/netbox-weather/20260917-baseline/` | 原插件压缩包、原配置、服务信息、新基础版本压缩包及安装文件 SHA-256；目录权限 0700 |

环境文件配置为 `NETBOX_PROJECT_ROOT=/opt/netbox/netbox` 和 `WEATHER_USER_AGENT="NetBox-OTNFaults/1.0 (zhenglei@263.net)"`。运行器只在同步进程内设置插件的 User-Agent，不影响其他插件配置。后续升级插件不会覆盖 `/opt/netbox-weather/` 和 systemd 单元，但必须保留新版本气象模块及其依赖；若调整 NetBox 部署路径，需要同步修改服务/环境文件。

气象服务专用代理为 `HTTP_PROXY=http://192.168.30.29:7890`、`HTTPS_PROXY=http://192.168.30.29:7890`；`NO_PROXY=localhost,127.0.0.1,::1,192.168.30.176`。这三项仅配置在上述环境文件中，不更改系统或 Web 服务代理。通过代理测试 MET 及天文台两个域名均返回 HTTP 200，保留证书校验。

### 验证结果

- 1150 个站点中，1149 个配置了坐标和区域，实际区域为 30 个省份/直辖市，均无父区域；成功生成并缓存 30 个省级代表点预报。
- 首次同步完成于北京时间 2026-09-17 17:16:38：天气 `ready`、失败样本 0，台风 `ready`。天文台目录成功解析，当前返回 0 条台风路径；不代表永久无台风。
- 独立 Django 进程可读取两个来源状态及全部 30 份天气缓存。初始天文台直连 HTTPS 探测有超时，正式同步已成功，随后按用户提供的信息配置气象服务专用代理。
- 后端气象测试在服务器虚拟环境中 10 项通过；前端气象测试在本地以无进程隔离方式运行，4 项通过；systemd 单元校验通过。
- `/maps/protomaps-z0-z6.pmtiles`、`/maps/china_provinces.pmtiles` HTTP 200；`otn_paths.pmtiles` 文件存在。
- 定时器已于北京时间 17:20:03 自动触发，17:20:10 完成；退出码 0，天气/台风均 `ready`，天气仍为 30 个样本、失败数 0。

### 运维与后续代码发布

```sh
# 查看下一次执行、最近结果及日志
systemctl list-timers netbox-dashboard-weather.timer
systemctl status netbox-dashboard-weather.service --no-pager
journalctl -u netbox-dashboard-weather.service -n 30 --no-pager

# 手动刷新：沿用已配置的邮箱及失败退出码检查
sudo systemctl start netbox-dashboard-weather.service

# 停用同步
sudo systemctl disable --now netbox-dashboard-weather.timer
```

timer 已启用不等于同步成功，须检查 service 结果以及日志中的两个来源状态。同一 service 不会重叠执行，应用另有共享缓存锁。缓存丢失后下次任务会重新生成，备份包不是实时预报归档。暂停 timer 不会终止已运行的同步；如需立即停止，另执行 `sudo systemctl stop netbox-dashboard-weather.service`，非正常终止遗留的缓存锁最长一小时自然过期，不要清空整个 Redis。

后续完整代码发布前按既有流程另做数据库备份（本次未做数据库备份或数据库变更）；安装插件及依赖、按该版本要求处理迁移和 `collectstatic`，再重启应用。随后验证 V2 的 `/plugins/otnfaults/dashboard-v2/weather/` 权限、来源状态、开关和实际地图显示。本次仅验收后台基础机制，不宣称新版大屏已发布或浏览器验收完成。

回退基础机制时，先停用 timer 并处理运行中的 service；如需恢复原插件，应在受控发布窗口使用 `plugin-before.tar.gz`，不能将旧插件覆盖到已经进一步升级的版本。`weather-foundation.tar.gz` 可用于重建本次基础版本，`installed.sha256` 用于文件核验。配置备份包含敏感数据，只保存在受限备份目录，不写入仓库。
