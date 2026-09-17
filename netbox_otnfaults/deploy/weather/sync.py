"""Run weather acquisition in the production NetBox environment."""
import json
import os
import sys
from pathlib import Path


def main() -> int:
    project = Path(os.environ.get('NETBOX_PROJECT_ROOT', '/opt/netbox/netbox'))
    sys.path.insert(0, str(project))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
    import django
    django.setup()
    from django.conf import settings
    from netbox_otnfaults.services.dashboard_weather import sync_weather

    agent = os.environ.get('WEATHER_USER_AGENT', '')
    if not agent or not ('@' in agent or 'https://' in agent):
        print('A maintenance contact is required in WEATHER_USER_AGENT.', flush=True)
        return 2
    settings.PLUGINS_CONFIG['netbox_otnfaults']['dashboard_v2_weather_user_agent'] = agent
    result = sync_weather()
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if result.get('skipped'):
        return 0
    return 0 if all(result.get(source, {}).get('state') == 'ready'
                    for source in ('weather', 'typhoon')) else 1


if __name__ == '__main__':
    raise SystemExit(main())
