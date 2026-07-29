# Dashboard Cutover WebGL Layers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace dashboard cutover HTML markers with MapLibre WebGL circle and symbol layers while preserving the yellow wrench appearance.

**Architecture:** `renderCutoverMarkers()` converts cutovers to one GeoJSON source and updates it with `setData()`. Two circle layers render the glow/core, while one symbol layer uses the existing cutover SVG registered as a MapLibre image; all three layers participate in the dashboard layer stack.

**Tech Stack:** JavaScript, MapLibre GL JS 5.4, GeoJSON, Python `unittest` source regression tests, CSS.

---

### Task 1: Lock the WebGL contract

**Files:**
- Create: `tests/test_dashboard_cutover_webgl_layers.py`

- [ ] **Step 1: Write the failing source regression tests**

```python
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_ENGINE_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "map_engine.js"
DASHBOARD_CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "dashboard.css"
DASHBOARD_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"

class DashboardCutoverWebGLLayersTestCase(unittest.TestCase):
    def test_cutovers_use_geojson_webgl_layers(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")
        renderer = source.split("function renderCutoverMarkers", 1)[1].split("function renderHeatmap", 1)[0]
        self.assertIn("map.addSource('cutovers'", renderer)
        self.assertIn("map.getSource('cutovers').setData(geojson)", renderer)
        for layer_id in ("cutovers-glow", "cutovers-core", "cutovers-icon"):
            self.assertIn(f"id: '{layer_id}'", renderer)
        self.assertNotIn("new maplibregl.Marker", renderer)
        self.assertNotIn("_cutoverMarkers", renderer)

    def test_cutover_wrench_is_registered_as_a_map_image(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")
        template = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("FAULT_SVG_ICONS.cutover", source)
        self.assertIn("map.addImage(CUTOVER_ICON_IMAGE_ID", source)
        self.assertIn("'icon-image': CUTOVER_ICON_IMAGE_ID", source)
        self.assertIn("js/utils/fault_icons.js", template)

    def test_cutover_layers_are_stacked_above_fault_layers(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")
        stack = source.split("const DASHBOARD_LAYER_STACK = [", 1)[1].split("];", 1)[0]
        ids = ["'faults-core'", "'cutovers-glow'", "'cutovers-core'", "'cutovers-icon'"]
        positions = [stack.index(layer_id) for layer_id in ids]
        self.assertEqual(positions, sorted(positions))

    def test_html_marker_styles_are_removed(self) -> None:
        css = DASHBOARD_CSS_PATH.read_text(encoding="utf-8")
        for selector in (".cutover-map-marker", ".cutover-marker-glow", ".cutover-marker-core"):
            self.assertNotIn(selector, css)
```

- [ ] **Step 2: Verify RED**

Run: `python tests/test_dashboard_cutover_webgl_layers.py`

Expected: failures for the missing source/layers/image and remaining HTML Marker code/CSS.

- [ ] **Step 3: Commit the failing tests**

Run:

```powershell
git add -- tests/test_dashboard_cutover_webgl_layers.py
git commit -m "test: 锁定态势大屏割接 WebGL 图层"
```

### Task 2: Implement WebGL rendering

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/dashboard/map_engine.js`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/dashboard.html`

- [ ] **Step 1: Load the SVG catalog before the map engine**

```html
<script src="{% static 'netbox_otnfaults/js/utils/fault_icons.js' %}"></script>
<script src="{% static 'netbox_otnfaults/js/dashboard/map_engine.js' %}"></script>
```

- [ ] **Step 2: Register a cached MapLibre image**

Add `CUTOVER_ICON_IMAGE_ID` and `_cutoverIconPromise`. Implement
`_registerCutoverIcon()` to render `window.FAULT_SVG_ICONS.cutover` into a
64 × 64 canvas, call `map.addImage(..., {pixelRatio: 2})`, revoke the Blob URL
on success/error, and resolve `false` on error so circle layers remain visible.

- [ ] **Step 3: Replace HTML markers**

Convert each valid coordinate to:

```javascript
{
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [numericLng, numericLat] },
    properties: { id: c.id }
}
```

Create/update a `cutovers` GeoJSON source. On first creation add
`cutovers-glow` and `cutovers-core` circle layers using `#f59e0b`, then register
and add `cutovers-icon` as a symbol layer with:

```javascript
layout: {
    'icon-image': CUTOVER_ICON_IMAGE_ID,
    'icon-size': 0.62 * mapTextScale,
    'icon-allow-overlap': true,
    'icon-ignore-placement': true,
}
```

Call `_restackDashboardLayers()` after synchronous layer creation and after the
asynchronous symbol layer is added.

- [ ] **Step 4: Extend the stack**

Append after `faults-core`:

```javascript
'cutovers-glow',
'cutovers-core',
'cutovers-icon',
```

- [ ] **Step 5: Verify JavaScript**

Run:

```powershell
python tests/test_dashboard_cutover_webgl_layers.py
node --check netbox_otnfaults/static/netbox_otnfaults/js/dashboard/map_engine.js
```

Expected: only the CSS-removal test may still fail; Node exits 0.

### Task 3: Remove obsolete CSS and verify

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/css/dashboard.css`
- Modify: `tests/test_dashboard_layer_order.py`

- [ ] **Step 1: Remove obsolete CSS**

Delete the three HTML Marker selector blocks, `cutover-pulse`,
`cutover-wiggle`, and their `screen-4k`/large-viewport overrides.

- [ ] **Step 2: Extend layer-order coverage**

Append the three cutover layer IDs after `'faults-core'` in `expected_order`.

- [ ] **Step 3: Run focused verification**

Run:

```powershell
python -m unittest tests/test_dashboard_cutover_webgl_layers.py tests/test_dashboard_layer_order.py tests/test_dashboard_situation_board.py
node --check netbox_otnfaults/static/netbox_otnfaults/js/dashboard/map_engine.js
git diff --check
```

Expected: all selected tests pass, Node and diff checks exit 0.

- [ ] **Step 4: Compare the dashboard baseline**

Run: `python -m unittest discover -s tests -p "test_dashboard*.py"`

Expected: no new failure beyond the approved pre-existing
`test_dashboard_fault_focus_zoom_is_above_site_label_threshold` failure.

- [ ] **Step 5: Commit**

Run:

```powershell
git add -- PLAN.md docs/superpowers/plans/2026-07-29-dashboard-cutover-webgl-layers.md netbox_otnfaults/static/netbox_otnfaults/js/dashboard/map_engine.js netbox_otnfaults/static/netbox_otnfaults/css/dashboard.css netbox_otnfaults/templates/netbox_otnfaults/dashboard.html tests/test_dashboard_layer_order.py
git commit -m "修复态势大屏割接 WebGL 图层对齐"
```
