# Import ArcGIS Sites Nearby Duplicate Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pre-import audit to `import_arcgis_sites.py` that logs existing NetBox site pairs within 100 meters before ArcGIS data import begins.

**Architecture:** Keep the new behavior inside the existing script, but extract the distance-based duplicate scan into a pure helper function so it can be reused both by the import workflow and by isolated unit tests. The runtime flow stays the same except for one new preflight logging block that runs after loading existing site coordinates and before iterating ArcGIS features.

**Tech Stack:** Python, NetBox extras scripts, Django ORM, unittest

---

### Task 1: Add a failing test for the pure nearby-scan helper

**Files:**
- Create: `D:\Src\netbox-otnfaults\tests\test_import_arcgis_sites.py`
- Modify: `D:\Src\netbox-otnfaults\netbox_otnfaults\scripts\import_arcgis_sites.py`
- Test: `D:\Src\netbox-otnfaults\tests\test_import_arcgis_sites.py`

- [ ] **Step 1: Write the failing test**

```python
def test_find_nearby_duplicate_pairs_returns_pairs_within_threshold(self) -> None:
    module = _load_script_module()
    pairs = module._find_nearby_duplicate_pairs(
        [
            ("A站", 25.0, 118.0),
            ("B站", 25.0003, 118.0003),
            ("C站", 26.0, 119.0),
        ],
        threshold_m=100.0,
    )
    self.assertEqual(len(pairs), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_import_arcgis_sites.ImportArcGISSitesHelperTestCase.test_find_nearby_duplicate_pairs_returns_pairs_within_threshold`
Expected: FAIL because `_find_nearby_duplicate_pairs` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def _find_nearby_duplicate_pairs(site_coords, threshold_m=100.0):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_import_arcgis_sites.ImportArcGISSitesHelperTestCase.test_find_nearby_duplicate_pairs_returns_pairs_within_threshold`
Expected: PASS

### Task 2: Add a failing test for the pre-import logging hook

**Files:**
- Modify: `D:\Src\netbox-otnfaults\tests\test_import_arcgis_sites.py`
- Modify: `D:\Src\netbox-otnfaults\netbox_otnfaults\scripts\import_arcgis_sites.py`
- Test: `D:\Src\netbox-otnfaults\tests\test_import_arcgis_sites.py`

- [ ] **Step 1: Write the failing test**

```python
def test_log_existing_nearby_duplicates_logs_warning_details(self) -> None:
    module = _load_script_module()
    script = _DummyScript()
    module._log_existing_nearby_duplicates(
        script,
        [("A站", 25.0, 118.0), ("B站", 25.0003, 118.0003)],
        threshold_m=100.0,
    )
    self.assertTrue(any(level == "warning" for level, _ in script.messages))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_import_arcgis_sites.ImportArcGISSitesLoggingTestCase.test_log_existing_nearby_duplicates_logs_warning_details`
Expected: FAIL because `_log_existing_nearby_duplicates` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def _log_existing_nearby_duplicates(script, site_coords, threshold_m=100.0):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_import_arcgis_sites.ImportArcGISSitesLoggingTestCase.test_log_existing_nearby_duplicates_logs_warning_details`
Expected: PASS

### Task 3: Wire the new preflight check into the import script

**Files:**
- Modify: `D:\Src\netbox-otnfaults\netbox_otnfaults\scripts\import_arcgis_sites.py`
- Test: `D:\Src\netbox-otnfaults\tests\test_import_arcgis_sites.py`

- [ ] **Step 1: Update the script flow**

```python
site_coords = list(
    Site.objects.filter(
        latitude__isnull=False, longitude__isnull=False
    ).values_list("name", "latitude", "longitude")
)
self.log_info(...)
_log_existing_nearby_duplicates(self, site_coords, threshold_m=100.0)
```

- [ ] **Step 2: Run focused tests**

Run: `python -m unittest tests.test_import_arcgis_sites -v`
Expected: PASS

- [ ] **Step 3: Run lightweight syntax validation**

Run: `python - <<'PY'\nimport ast\nfrom pathlib import Path\npath = Path(r'D:\Src\netbox-otnfaults\netbox_otnfaults\scripts\import_arcgis_sites.py')\nast.parse(path.read_text(encoding='utf-8'))\nprint('AST_OK')\nPY`
Expected: `AST_OK`
