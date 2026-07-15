from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_cutover_impact_edit_uses_standard_netbox_change_permission() -> None:
    views = _read("netbox_otnfaults/views.py")
    view_source = views.split("class CutoverImpactEditView", 1)[1].split(
        "class CutoverImpactDeleteView", 1
    )[0]

    assert "def post(" not in view_source
    assert "line_supervisor" not in view_source
    assert "business_manager" not in view_source
    assert "request.user.is_superuser" not in view_source
    assert "show_permission_denied_modal" not in view_source


def test_cutover_impact_edit_template_has_no_identity_denied_modal() -> None:
    template = _read(
        "netbox_otnfaults/templates/netbox_otnfaults/cutoverimpact_edit.html"
    )

    assert "permissionDeniedModal" not in template
    assert "show_permission_denied_modal" not in template


if __name__ == "__main__":
    test_cutover_impact_edit_uses_standard_netbox_change_permission()
    test_cutover_impact_edit_template_has_no_identity_denied_modal()
