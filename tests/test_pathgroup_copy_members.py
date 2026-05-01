import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"
URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "urls.py"
TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "otnpathgroup.html"
)


class PathGroupCopyMembersSourceTestCase(unittest.TestCase):
    def test_copy_form_exposes_source_group_and_mode(self) -> None:
        source = FORMS_PATH.read_text(encoding="utf-8")

        self.assertIn("class OtnPathGroupCopyMembersForm", source)
        self.assertIn("source_group = DynamicModelChoiceField", source)
        self.assertIn("mode = forms.ChoiceField", source)
        self.assertIn("('merge', '保留现有站点与路径并合并复制')", source)
        self.assertIn("('replace', '覆盖现有站点与路径后复制')", source)
        self.assertIn("queryset=OtnPathGroup.objects.none()", source)
        self.assertIn("exclude(pk=target_group.pk)", source)
        self.assertIn("不能选择当前路径组作为来源", source)

    def test_copy_view_copies_paths_and_site_metadata(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("class OtnPathGroupCopyMembersView", source)
        self.assertIn("permission_required = 'netbox_otnfaults.change_otnpathgroup'", source)
        self.assertIn("transaction.atomic()", source)
        self.assertIn("if mode == 'replace':", source)
        self.assertIn("target_group.paths.clear()", source)
        self.assertIn("target_group.group_sites.all().delete()", source)
        self.assertIn("target_group.paths.add(*source_group.paths.all())", source)
        self.assertIn("existing_site_ids = set(", source)
        self.assertIn("source_group.group_sites.order_by('position', 'pk')", source)
        self.assertIn("role=source_site.role", source)
        self.assertIn("position=source_site.position", source)
        self.assertIn("comments=source_site.comments", source)
        self.assertIn("messages.success", source)

    def test_copy_url_and_detail_button_are_registered(self) -> None:
        urls_source = URLS_PATH.read_text(encoding="utf-8")
        template_source = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "path('path-groups/<int:pk>/copy-members/'",
            urls_source,
        )
        self.assertIn("OtnPathGroupCopyMembersView.as_view()", urls_source)
        self.assertIn("name='otnpathgroup_copy_members'", urls_source)
        self.assertIn("otnpathgroup_copy_members", template_source)
        self.assertIn("复制路径组", template_source)
        self.assertIn("mdi-content-copy", template_source)


if __name__ == "__main__":
    unittest.main()
