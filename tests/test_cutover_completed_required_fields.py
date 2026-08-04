import unittest
import importlib.util
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_MODULE = (
    REPO_ROOT / 'netbox_otnfaults' / 'services' / 'cutover_completion.py'
)
CUTOVER_EDIT_TEMPLATE = (
    REPO_ROOT
    / 'netbox_otnfaults'
    / 'templates'
    / 'netbox_otnfaults'
    / 'cutovertask_edit.html'
)


def load_validation_module() -> ModuleType:
    assert VALIDATION_MODULE.exists(), 'cutover completion validator is missing'
    spec = importlib.util.spec_from_file_location('cutover_completion', VALIDATION_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError('无法加载割接完成状态校验模块。')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_completed_cutover_returns_all_missing_fields() -> None:
    module = load_validation_module()

    assert module.find_missing_cutover_completion_fields(
        {'status': 'completed'},
        completed_status='completed',
    ) == (
        'started_at',
        'completed_at',
        'closed_at',
        'is_timeout',
        'cutover_result',
        'rectification_status',
    )


def test_completed_cutover_returns_only_missing_fields() -> None:
    module = load_validation_module()
    values = {
        'status': 'completed',
        'started_at': object(),
        'completed_at': object(),
        'closed_at': object(),
        'is_timeout': 'no',
        'cutover_result': '',
        'rectification_status': '',
    }

    assert module.find_missing_cutover_completion_fields(
        values,
        completed_status='completed',
    ) == ('cutover_result', 'rectification_status')


def test_completed_cutover_with_all_fields_returns_no_missing_fields() -> None:
    module = load_validation_module()
    values = {
        'status': 'completed',
        **{
            field_name: object()
            for field_name in module.CUTOVER_COMPLETION_REQUIRED_FIELDS
        },
    }

    assert module.find_missing_cutover_completion_fields(
        values,
        completed_status='completed',
    ) == ()


def test_non_completed_cutover_does_not_require_completion_fields() -> None:
    module = load_validation_module()

    assert module.find_missing_cutover_completion_fields(
        {'status': 'pending_implementation'},
        completed_status='completed',
    ) == ()


def test_cutover_form_binds_every_missing_completion_field_error() -> None:
    forms_source = (REPO_ROOT / 'netbox_otnfaults' / 'forms.py').read_text(
        encoding='utf-8'
    )
    form_source = forms_source.split(
        'class CutoverTaskForm(NetBoxModelForm):', 1
    )[1].split('class CutoverTaskFilterForm', 1)[0]

    assert 'find_missing_cutover_completion_fields(' in form_source
    assert 'completed_status=CutoverStatusChoices.COMPLETED' in form_source
    assert 'self.add_error(field_name, CUTOVER_COMPLETION_REQUIRED_ERROR)' in form_source
    assert 'return cleaned_data' in form_source

def test_cutover_edit_marks_each_completion_field_error_inline() -> None:
    module = load_validation_module()
    template = CUTOVER_EDIT_TEMPLATE.read_text(encoding='utf-8')
    for field_name in module.CUTOVER_COMPLETION_REQUIRED_FIELDS:
        assert f'form.{field_name}.errors' in template
        assert f'data-cutover-completion-error-for="id_{field_name}"' in template
    assert 'inc/form_errors.html' not in template


def test_cutover_edit_scrolls_and_focuses_first_completion_error() -> None:
    template = CUTOVER_EDIT_TEMPLATE.read_text(encoding='utf-8')
    assert 'function focusFirstCutoverCompletionError()' in template
    assert "document.querySelector('[data-cutover-completion-error-for]')" in template
    assert 'marker.dataset.cutoverCompletionErrorFor' in template
    assert "scrollIntoView({ behavior: 'smooth', block: 'center' })" in template
    assert 'field.tomselect.focus();' in template
    assert 'field.focus({ preventScroll: true });' in template
    assert 'setTimeout(focusFirstCutoverCompletionError, 200);' in template



class CutoverCompletedRequiredFieldsTestCase(unittest.TestCase):
    def test_completed_cutover_returns_all_missing_fields(self) -> None:
        test_completed_cutover_returns_all_missing_fields()

    def test_completed_cutover_returns_only_missing_fields(self) -> None:
        test_completed_cutover_returns_only_missing_fields()

    def test_completed_cutover_with_all_fields_returns_no_missing_fields(self) -> None:
        test_completed_cutover_with_all_fields_returns_no_missing_fields()

    def test_non_completed_cutover_does_not_require_completion_fields(self) -> None:
        test_non_completed_cutover_does_not_require_completion_fields()

    def test_cutover_form_binds_every_missing_completion_field_error(self) -> None:
        test_cutover_form_binds_every_missing_completion_field_error()

    def test_cutover_edit_marks_each_completion_field_error_inline(self) -> None:
        test_cutover_edit_marks_each_completion_field_error_inline()

    def test_cutover_edit_scrolls_and_focuses_first_completion_error(self) -> None:
        test_cutover_edit_scrolls_and_focuses_first_completion_error()



if __name__ == '__main__':
    unittest.main()
