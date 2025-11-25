# NetBox OTN Faults Plugin

NetBox 插件，用于 OTN 网络故障登记。

## 功能
- 故障登记：自动生成编号，记录故障时间、位置、分类、原因等。
- 故障影响业务：记录故障影响的租户业务及中断时长。
- 自动计算中断历时。
- 全中文界面。

## 安装

1. 激活 NetBox 虚拟环境。
2. 安装插件：
   ```bash
   pip install .
   ```
3. 在 `configuration.py` 中启用插件：
   ```python
   PLUGINS = ['netbox_otnfaults']
   ```
4. 运行数据库迁移：
   ```bash
   python manage.py makemigrations netbox_otnfaults
   python manage.py migrate
   ```

## 使用
在导航栏中找到 "OTN故障登记" 进行操作。
