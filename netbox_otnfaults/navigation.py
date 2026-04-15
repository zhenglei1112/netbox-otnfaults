from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton

menu = PluginMenu(
    label='故障管理',
    groups=(
        ('故障', (
            PluginMenuItem(
                link='plugins:netbox_otnfaults:otnfault_list',
                link_text='故障登记',
                permissions=['netbox_otnfaults.view_otnfault'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_otnfaults:otnfault_add',
                        title='添加',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_otnfaults.add_otnfault'],
                    ),
                )
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:otnfaultimpact_list',
                link_text='故障影响业务',
                permissions=['netbox_otnfaults.view_otnfaultimpact'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_otnfaults:otnfaultimpact_add',
                        title='添加',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_otnfaults.add_otnfaultimpact'],
                    ),
                )
            ),
        )),
        ('业务', (
            PluginMenuItem(
                link='plugins:netbox_otnfaults:barefiberservice_list',
                link_text='裸纤业务',
                permissions=['netbox_otnfaults.view_barefiberservice'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_otnfaults:barefiberservice_add',
                        title='添加',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_otnfaults.add_barefiberservice'],
                    ),
                )
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:circuitservice_list',
                link_text='电路业务',
                permissions=['netbox_otnfaults.view_circuitservice'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_otnfaults:circuitservice_add',
                        title='添加',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_otnfaults.add_circuitservice'],
                    ),
                )
            ),
        )),
        ('路径', (
            PluginMenuItem(
                link='plugins:netbox_otnfaults:otnpathgroup_list',
                link_text='路径组',
                permissions=['netbox_otnfaults.view_otnpathgroup'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_otnfaults:otnpathgroup_add',
                        title='添加',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_otnfaults.add_otnpathgroup'],
                    ),
                )
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:otnpath_list',
                link_text='路径管理',
                permissions=['netbox_otnfaults.view_otnpath'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_otnfaults:otnpath_add',
                        title='添加',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_otnfaults.add_otnpath'],
                    ),
                )
            ),
        )),
        ('地图', (
            PluginMenuItem(
                link='plugins:netbox_otnfaults:otnfault_map_globe',
                link_text='故障分布图',
                permissions=['netbox_otnfaults.view_otnfault'],
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:route_editor',
                link_text='线路设计器',
                permissions=['netbox_otnfaults.view_otnpath'],
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:dashboard',
                link_text='态势大屏',
                permissions=['netbox_otnfaults.view_otnfault'],
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:weekly_report',
                link_text='光缆故障每周通报',
                permissions=['netbox_otnfaults.view_otnfault'],
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:statistics',
                link_text='故障统计',
                permissions=['netbox_otnfaults.view_otnfault'],
            ),
        )),
    ),
    icon_class='mdi mdi-tools',
)
