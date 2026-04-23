from .models import FaultCategoryChoices, FaultStatusChoices


BOOTSTRAP_COLOR_HEX: dict[str, str] = {
    'dark': '#343a40',
    'gray': '#6c757d',
    'light-gray': '#aaacae',
    'blue': '#0d6efd',
    'indigo': '#6610f2',
    'purple': '#6f42c1',
    'pink': '#d63384',
    'red': '#dc3545',
    'orange': '#f5a623',
    'yellow': '#ffc107',
    'green': '#198754',
    'teal': '#20c997',
    'cyan': '#0dcaf0',
    'white': '#ffffff',
    'secondary': '#6c757d',
}


def get_hex_color(color_name: str | None) -> str:
    """Map NetBox/Bootstrap color names to Hex values."""
    return BOOTSTRAP_COLOR_HEX.get(color_name or '', '#6c757d')


def build_fault_colors_config() -> dict[str, dict[str, str]]:
    """Build the shared color config used by unified map pages."""
    return {
        'category_colors': {
            value: get_hex_color(color)
            for value, _label, color in FaultCategoryChoices.CHOICES
        },
        'category_names': {
            value: label
            for value, label, _color in FaultCategoryChoices.CHOICES
        },
        'status_colors': {
            value: get_hex_color(color)
            for value, _label, color in FaultStatusChoices.CHOICES
        },
        'status_names': {
            value: label
            for value, label, _color in FaultStatusChoices.CHOICES
        },
        'popup_status_colors': {
            key: get_hex_color(key)
            for key in ['orange', 'blue', 'yellow', 'green', 'gray', 'red', 'secondary', 'purple']
        },
    }
