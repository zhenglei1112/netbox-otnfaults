path = r'd:\Src\netbox-otnfaults\netbox_otnfaults\templates\netbox_otnfaults\otnfault.html'
content = open(path, 'r', encoding='utf-8').read()

# 1. Add id="site-history" anchor to the card div
content = content.replace(
    '<div class="row mb-3">\n  <div class="col col-md-12">\n    <div class="card">\n      <style>.site-faults-table-container',
    '<div class="row mb-3" id="site-history">\n  <div class="col col-md-12">\n    <div class="card">\n      <style>.site-faults-table-container'
)

# 2. Add #site-history to all filter button links
content = content.replace('href="?site_time_filter=all"', 'href="?site_time_filter=all#site-history"')
content = content.replace('href="?site_time_filter=this_week"', 'href="?site_time_filter=this_week#site-history"')
content = content.replace('href="?site_time_filter=this_month"', 'href="?site_time_filter=this_month#site-history"')
content = content.replace('href="?site_time_filter=this_year"', 'href="?site_time_filter=this_year#site-history"')
content = content.replace('href="?site_time_filter=last_7_days"', 'href="?site_time_filter=last_7_days#site-history"')
content = content.replace('href="?site_time_filter=last_30_days"', 'href="?site_time_filter=last_30_days#site-history"')

# 3. Add #site-history to all pagination links
content = content.replace('&site_per_page={{ site_per_page }}"', '&site_per_page={{ site_per_page }}#site-history"')
content = content.replace('&site_per_page=25"', '&site_per_page=25#site-history"')
content = content.replace('&site_per_page=50"', '&site_per_page=50#site-history"')
content = content.replace('&site_per_page=100"', '&site_per_page=100#site-history"')
content = content.replace('&site_per_page=250"', '&site_per_page=250#site-history"')
content = content.replace('&site_per_page=500"', '&site_per_page=500#site-history"')

open(path, 'w', encoding='utf-8').write(content)
print('Done')
