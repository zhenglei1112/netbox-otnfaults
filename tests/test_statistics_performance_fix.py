import datetime as dt
import importlib.util
from pathlib import Path
import sys
import types
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
UTILS_PATH = REPO_ROOT / "netbox_otnfaults" / "utils.py"


def _install_import_stubs():
    if "netbox_otnfaults.models" in sys.modules:
        return

    netbox_module = types.ModuleType("netbox")
    plugins_module = types.ModuleType("netbox.plugins")
    plugins_module.PluginConfig = type("PluginConfig", (), {})
    netbox_module.plugins = plugins_module
    sys.modules["netbox"] = netbox_module
    sys.modules["netbox.plugins"] = plugins_module

    plugin_module = types.ModuleType("netbox_otnfaults")
    plugin_module.__path__ = [str(REPO_ROOT / "netbox_otnfaults")]
    models_module = types.ModuleType("netbox_otnfaults.models")
    models_module.FaultCategoryChoices = type("FaultCategoryChoices", (), {
        "FIBER_BREAK": "fiber_break",
        "FIBER_DEGRADATION": "fiber_degradation",
        "FIBER_JITTER": "fiber_jitter",
    })
    models_module.FaultStatusChoices = type("FaultStatusChoices", (), {"SUSPENDED": "suspended"})
    sys.modules["netbox_otnfaults"] = plugin_module
    sys.modules["netbox_otnfaults.models"] = models_module


def _load_utils_module():
    _install_import_stubs()
    spec = importlib.util.spec_from_file_location("netbox_otnfaults.utils", UTILS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    module.__package__ = "netbox_otnfaults"
    sys.modules["netbox_otnfaults.utils"] = module
    spec.loader.exec_module(module)
    return module


utils_mod = _load_utils_module()
detect_repeat_faults = utils_mod.detect_repeat_faults


class MockSite:
    def __init__(self, site_id: int):
        self.id = site_id


class MockFault:
    def __init__(self, fault_id: int, a_id: int, z_ids: list[int], occ_time: dt.datetime, is_fiber: bool = True):
        self.id = fault_id
        self.interruption_location_a_id = a_id
        self._z_sites = [MockSite(z) for z in z_ids]
        self.fault_occurrence_time = occ_time
        self.is_fiber_fault = is_fiber

    @property
    def interruption_location(self):
        class LocationRel:
            def __init__(self, sites):
                self._sites = sites
            def all(self):
                return self._sites
        return LocationRel(self._z_sites)


class StatisticsPerformanceFixTestCase(unittest.TestCase):
    def test_detect_repeat_faults_accuracy(self):
        """验证优化后的重复故障算法能正确识别 60 天内的重复故障"""
        now = dt.datetime(2026, 9, 17, 12, 0, 0)
        
        # 故障 1：站点 1 -> [10, 11]，发生于 10 天前
        f1 = MockFault(1, a_id=1, z_ids=[10, 11], occ_time=now - dt.timedelta(days=10))
        # 故障 2：站点 1 -> [11]，发生于当前，属于重复故障（与 f1 重合）
        f2 = MockFault(2, a_id=1, z_ids=[11], occ_time=now)
        # 故障 3：站点 2 -> [20]，发生于当前，不重复
        f3 = MockFault(3, a_id=2, z_ids=[20], occ_time=now)
        # 故障 4：站点 1 -> [10]，发生于 90 天前，超出 60 天窗口，不构成重复
        f4 = MockFault(4, a_id=1, z_ids=[10], occ_time=now - dt.timedelta(days=90))

        result = detect_repeat_faults([f2, f3], [f1, f4])
        self.assertIn(2, result.kpi_repeat_ids)
        self.assertIn(2, result.ui_repeat_ids)
        self.assertNotIn(3, result.kpi_repeat_ids)
        self.assertNotIn(3, result.ui_repeat_ids)

    def test_detect_repeat_faults_deduplication(self):
        """验证传入重复的 preceding 列表时不会因列表重复导致误判或膨胀"""
        now = dt.datetime(2026, 9, 17, 12, 0, 0)
        f_past = MockFault(1, a_id=1, z_ids=[10], occ_time=now - dt.timedelta(days=15))
        f_curr = MockFault(2, a_id=1, z_ids=[10], occ_time=now)

        # 模拟调用方重复传递 preceding_faults 的场景
        result = detect_repeat_faults([f_curr], [f_past], preceding_faults=[f_past])
        self.assertIn(2, result.kpi_repeat_ids)
        self.assertEqual(len(result.matched_preceding_faults), 1)
        self.assertEqual(result.matched_preceding_faults[0].id, 1)

    def test_frontend_lazy_loading_and_snapshot_implemented(self):
        """验证前端 statistics_dashboard.js 实现了统一筛选快照与明细按需懒加载"""
        js_path = (
            REPO_ROOT
            / "netbox_otnfaults"
            / "static"
            / "netbox_otnfaults"
            / "js"
            / "statistics_dashboard.js"
        )
        content = js_path.read_text(encoding="utf-8")

        # 验证筛选快照与活动 Tab 判定函数
        self.assertIn("function getFilterSnapshot()", content)
        self.assertIn("function getFilterSnapshotKey()", content)
        self.assertIn("function getActiveTabType()", content)
        self.assertIn("function loadActiveTabDetails(snapshot)", content)
        
        # [P1] 验证 loadData 支持请求版本校验与快照透传
        self.assertIn("const requestId = ++loadDataRequest;", content)
        self.assertIn("if (requestId !== loadDataRequest)", content)
        self.assertIn("loadActiveTabDetails(snapshot);", content)

        # [P2] 验证明细加载支持跨周期在途请求失效校验
        self.assertIn("snapshotKey !== activeDataSnapshotKey", content)
        self.assertIn("loadedDetailSnapshots.supervisor = snapshotKey;", content)
        self.assertIn("loadedDetailSnapshots.branch = snapshotKey;", content)
        self.assertIn("loadedDetailSnapshots.physical = snapshotKey;", content)

        # [P3] 验证汇总失败后状态置为 failed 且切 Tab 允许重新加载
        self.assertIn("dataLoadState = 'failed';", content)
        self.assertIn("dataLoadState !== 'success' || activeDataSnapshotKey !== snapKey", content)

    def test_frontend_diagnostics_thresholds(self):
        """验证诊断脚本 statistics_diagnostics.js 包含绝对耗时和排队等待告警"""
        diag_js_path = (
            REPO_ROOT
            / "netbox_otnfaults"
            / "static"
            / "netbox_otnfaults"
            / "js"
            / "statistics_diagnostics.js"
        )
        content = diag_js_path.read_text(encoding="utf-8")

        self.assertIn("row.complete_ms >= 2000", content)
        self.assertIn("视图外等待严重", content)
        self.assertIn("数据库执行占后端耗时超过50%", content)

    def test_detect_repeat_faults_benchmark(self):
        """性能复测：验证大规模数据量（3000+条）下，detect_repeat_faults 算法耗时达到 PRD 目标（<100ms）"""
        import time
        now = dt.datetime(2026, 9, 17, 12, 0, 0)
        # 构造 2000 个历史故障和 1000 个当前故障
        preceding = [
            MockFault(
                fault_id=i,
                a_id=i % 100,
                z_ids=[(i % 100) + 1, (i % 100) + 2],
                occ_time=now - dt.timedelta(days=(i % 55) + 1)
            )
            for i in range(1, 2001)
        ]
        current = [
            MockFault(
                fault_id=10000 + j,
                a_id=j % 100,
                z_ids=[(j % 100) + 1],
                occ_time=now - dt.timedelta(hours=(j % 24))
            )
            for j in range(1, 1001)
        ]

        start_time = time.perf_counter()
        result = detect_repeat_faults(current, preceding)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # 3000 条对象比对耗时应大幅低于 100ms
        self.assertLess(elapsed_ms, 100.0, f"detect_repeat_faults 耗时超标: {elapsed_ms:.2f}ms >= 100ms")
        self.assertGreater(len(result.kpi_repeat_ids), 0)

    def test_async_concurrency_node_suite(self):
        """执行前端异步并发深度测试套件，验证乱序竞争、在途失效与失败重试"""
        import subprocess
        res = subprocess.run(
            ["node", "tests/test_statistics_async_concurrency.js"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(res.returncode, 0, f"异步并发测试失败:\n{res.stdout}\n{res.stderr}")
        self.assertIn("# pass 3", res.stdout)
        self.assertIn("# fail 0", res.stdout)


if __name__ == "__main__":
    unittest.main()
