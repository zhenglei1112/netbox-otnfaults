
    def _get_hex_color(self, color_name):
        """Map standard NetBox/Bootstrap color names to Hex values."""
        COLOR_MAP = {
            'dark': '#343a40',
            'gray': '#6c757d',
            'light-gray': '#aaacae',
            'blue': '#0d6efd',
            'indigo': '#6610f2',
            'purple': '#6f42c1',
            'pink': '#d63384',
            'red': '#dc3545',
            'orange': '#f5a623', # Using the project's preferred orange
            'yellow': '#ffc107',
            'green': '#198754',
            'teal': '#20c997',
            'cyan': '#0dcaf0',
            'white': '#ffffff',
            'secondary': '#6c757d',
        }
        return COLOR_MAP.get(color_name, '#6c757d') # Default to gray
