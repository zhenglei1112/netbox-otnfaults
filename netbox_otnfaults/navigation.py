from netbox.plugins import PluginMenuItem, PluginMenuButton

menu_items = (
    PluginMenuItem(
        link='plugins:netbox_otnfaults:otnfault_list',
        link_text='故障登记',
        buttons=(
            PluginMenuButton(
                link='plugins:netbox_otnfaults:otnfault_add',
                title='添加',
                icon_class='mdi mdi-plus-thick',
            ),
        )
    ),
    PluginMenuItem(
        link='plugins:netbox_otnfaults:otnfaultimpact_list',
        link_text='故障影响业务',
        buttons=(
            PluginMenuButton(
                link='plugins:netbox_otnfaults:otnfaultimpact_add',
                title='添加',
                icon_class='mdi mdi-plus-thick',
            ),
        )
    ),
)
