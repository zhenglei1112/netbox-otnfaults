import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_FILE = REPO_ROOT / "netbox_otnfaults" / "models.py"
VIEWS_FILE = REPO_ROOT / "netbox_otnfaults" / "views.py"
DETAIL_TEMPLATE = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "cutovertask.html"


class CutoverStatusAutoSetTestCase(unittest.TestCase):
    def test_cutover_task_model_auto_set_status(self) -> None:
        """测试 models.py 中 CutoverTask.save() 是否包含当影响业务全部已批准或强制割接时自动流转为待实施状态的逻辑"""
        models_source = MODELS_FILE.read_text(encoding="utf-8")
        
        self.assertIn("class CutoverTask(NetBoxModel, ImageAttachmentsMixin):", models_source)
        self.assertIn("def save(self, *args: Any, **kwargs: Any) -> None:", models_source)
        
        # 验证条件检测和状态设置
        self.assertIn("impacts = self.impacts.all()", models_source)
        self.assertIn("if impacts.exists() and not impacts.exclude(coordination_status__in=['approved', 'forced']).exists():", models_source)
        self.assertIn("self.status = CutoverStatusChoices.PENDING_IMPLEMENTATION", models_source)

    def test_cutover_task_edit_view_sends_show_modal_message(self) -> None:
        """测试 views.py 中 CutoverTaskEditView.post() 是否能正确截获状态变更为 pending_implementation，并把标识存入 session"""
        views_source = VIEWS_FILE.read_text(encoding="utf-8")
        
        self.assertIn("class CutoverTaskEditView(generic.ObjectEditView):", views_source)
        self.assertIn("def post(self, request, *args, **kwargs):", views_source)
        self.assertIn("old_status = obj.status", views_source)
        self.assertIn("response = super().post(request, *args, **kwargs)", views_source)
        self.assertIn("obj.refresh_from_db()", views_source)
        self.assertIn("if old_status != 'pending_implementation' and new_status == 'pending_implementation':", views_source)
        self.assertIn("request.session['cutover_auto_set_pending'] = True", views_source)

    def test_cutover_task_detail_renders_countdown_modal(self) -> None:
        """测试 cutovertask.html 中是否包含 3 秒倒计时自动关闭模态提示框的前端代码"""
        template_source = DETAIL_TEMPLATE.read_text(encoding="utf-8")
        
        # 验证模态框 HTML 及 CSS
        self.assertIn('id="cutoverStatusNoticeModal"', template_source)
        self.assertIn("所有影响业务均已批准（含强制割接），本次割接状态已被自动设置为待实施", template_source)
        
        # 验证倒计时关闭 JS 逻辑
        self.assertIn("window.showCutoverStatusNoticeModal = function()", template_source)
        self.assertIn("window.hideCutoverStatusNoticeModal = function()", template_source)
        self.assertIn("let timeLeft = 3;", template_source)
        self.assertIn("countdownTimer = setInterval(function() {", template_source)
        self.assertIn("show_auto_set_pending", template_source)

    def test_cutover_task_applying_hides_sections(self) -> None:
        """测试在 status=='applying' (申请中) 时隐藏时间线、闭环、整改三组信息"""
        # 1. 验证详情页中的 Django 状态判断包裹
        template_source = DETAIL_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("object.status != 'applying'", template_source)
        
        # 2. 验证编辑页中的组 id 与 js 逻辑注入
        edit_template_file = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "cutovertask_edit.html"
        edit_template_source = edit_template_file.read_text(encoding="utf-8")
        
        self.assertIn('id="group_implementation_timeline"', edit_template_source)
        self.assertIn('id="group_assessment_closure"', edit_template_source)
        self.assertIn('id="group_rectification_info"', edit_template_source)
        self.assertIn("function initStatusSectionToggle()", edit_template_source)
        self.assertIn("currentStatus === 'applying'", edit_template_source)


if __name__ == "__main__":
    unittest.main()
