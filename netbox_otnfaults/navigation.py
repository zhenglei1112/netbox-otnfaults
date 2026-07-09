from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton

menu = PluginMenu(
    label='故障与割接',
    groups=(
        ('运行态势', (
            PluginMenuItem(
                link='plugins:netbox_otnfaults:dashboard',
                link_text='态势大屏',
                permissions=['netbox_otnfaults.view_otnfault'],
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:otnfault_map_globe',
                link_text='一张图',
                permissions=['netbox_otnfaults.view_otnfault'],
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:statistics',
                link_text='故障统计',
                permissions=['netbox_otnfaults.view_otnfault'],
            ),
        )),
        ('故障处置', (
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
        ('割接管理', (
            PluginMenuItem(
                link='plugins:netbox_otnfaults:cutovertask_list',
                link_text='割接任务',
                permissions=['netbox_otnfaults.view_cutovertask'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_otnfaults:cutovertask_add',
                        title='添加',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_otnfaults.add_cutovertask'],
                    ),
                )
            ),
            PluginMenuItem(
                link='plugins:netbox_otnfaults:cutoverimpact_list',
                link_text='割接影响业务',
                permissions=['netbox_otnfaults.view_cutoverimpact'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_otnfaults:cutoverimpact_add',
                        title='添加',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_otnfaults.add_cutoverimpact'],
                    ),
                )
            ),
        )),
        ('保障任务', (
            PluginMenuItem(
                link='plugins:netbox_otnfaults:heavyduty_list',
                link_text='重要保障',
                permissions=['netbox_otnfaults.view_heavyduty'],
                buttons=(
                    PluginMenuButton(
                        link='plugins:netbox_otnfaults:heavyduty_add',
                        title='添加',
                        icon_class='mdi mdi-plus-thick',
                        permissions=['netbox_otnfaults.add_heavyduty'],
                    ),
                )
            ),
        )),
        ('业务资源', (
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
        )),
        ('网络资源', (
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
                link_text='光缆路径',
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
            PluginMenuItem(
                link='plugins:netbox_otnfaults:route_editor',
                link_text='线路设计器',
                permissions=['netbox_otnfaults.view_otnpath'],
            ),
        )),
    ),
    icon_class='mdi mdi-tools',
)
