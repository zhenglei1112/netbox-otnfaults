from typing import Any

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from .services.dashboard_v2 import build_dashboard_v2_data


def _get_dashboard_v2_config() -> dict[str, Any]:
    plugin_settings: dict[str, Any] = settings.PLUGINS_CONFIG.get("netbox_otnfaults", {})
    return {
        "mapCenter": plugin_settings.get("dashboard_v2_map_center", [103.0, 34.3]),
        "mapZoom": plugin_settings.get("dashboard_v2_map_zoom", 4.0),
        "mapBearing": plugin_settings.get("dashboard_v2_map_bearing", 0.0),
        "basemapMode": plugin_settings.get(
            "dashboard_v2_basemap_mode", "protomaps"
        ),
        "protomapsTilesUrl": plugin_settings.get(
            "dashboard_v2_protomaps_tiles_url",
            "/maps/protomaps-z0-z6.pmtiles",
        ),
        "otnPathsPmtilesUrl": plugin_settings.get(
            "otn_paths_pmtiles_url", "/maps/otn_paths.pmtiles"
        ),
        "chinaProvincesPmtilesUrl": plugin_settings.get(
            "dashboard_v2_china_provinces_pmtiles_url",
            "/maps/china_provinces.pmtiles",
        ),
        "useLocalBasemap": plugin_settings.get("use_local_basemap", False),
        "localTilesUrl": plugin_settings.get("local_tiles_url", "/maps/china.pmtiles"),
        "localGlyphsUrl": plugin_settings.get(
            "local_glyphs_url", "/maps/fonts/{fontstack}/{range}.pbf"
        ),
        "dataUrl": reverse("plugins:netbox_otnfaults:dashboard_v2_data"),
    }


class DashboardV2PageView(PermissionRequiredMixin, View):
    permission_required = "netbox_otnfaults.view_otnfault"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "netbox_otnfaults/dashboard_v2.html",
            {"dashboard_v2_config": _get_dashboard_v2_config()},
        )


class DashboardV2DataView(PermissionRequiredMixin, View):
    permission_required = "netbox_otnfaults.view_otnfault"

    def get(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse(
            build_dashboard_v2_data(sites_version=request.GET.get("sites_version")),
            json_dumps_params={"ensure_ascii": False},
        )
