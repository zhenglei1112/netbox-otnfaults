import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
SERIALIZERS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "serializers.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "circuitservice_edit.html"


def _parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Class {class_name} not found")


def _find_assignment(class_node: ast.ClassDef, target_name: str) -> ast.AST:
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == target_name:
                    return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == target_name:
            return node.value
    raise AssertionError(f"Assignment {target_name} not found in {class_node.name}")


def _find_meta_tuple(class_node: ast.ClassDef, field_name: str, attr_name: str = "fields") -> None:
    meta_class = _find_class(ast.Module(body=class_node.body, type_ignores=[]), "Meta")
    value = _find_assignment(meta_class, attr_name)
    if not isinstance(value, (ast.Tuple, ast.List)):
        raise AssertionError(f"{class_node.name}.Meta.{attr_name} is not a tuple/list")
    items = [elt.value for elt in value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
    if field_name not in items:
        raise AssertionError(f"{field_name} not found in {class_node.name}.Meta.{attr_name}")


class CircuitServiceExternalBusinessSourceTestCase(unittest.TestCase):
    def test_model_declares_boolean_field_with_false_default(self) -> None:
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "CircuitService")
        value = _find_assignment(class_node, "is_external_business")

        self.assertIsInstance(value, ast.Call)
        self.assertIsInstance(value.func, ast.Attribute)
        self.assertEqual(value.func.attr, "BooleanField")

        keyword_names = {kw.arg for kw in value.keywords}
        self.assertIn("default", keyword_names)
        self.assertIn("verbose_name", keyword_names)

        default_kw = next(kw for kw in value.keywords if kw.arg == "default")
        verbose_kw = next(kw for kw in value.keywords if kw.arg == "verbose_name")
        self.assertIs(default_kw.value.value, False)
        self.assertEqual(verbose_kw.value.value, "对部服务")

    def test_forms_include_external_business_field(self) -> None:
        module = _parse_module(FORMS_PATH)

        for class_name in ("CircuitServiceForm", "CircuitServiceImportForm"):
            class_node = _find_class(module, class_name)
            _find_meta_tuple(class_node, "is_external_business")

        bulk_edit_class = _find_class(module, "CircuitServiceBulkEditForm")
        _find_assignment(bulk_edit_class, "is_external_business")

        filter_form_class = _find_class(module, "CircuitServiceFilterForm")
        _find_assignment(filter_form_class, "is_external_business")

    def test_filterset_serializer_and_table_include_external_business(self) -> None:
        filtersets_module = _parse_module(FILTERSETS_PATH)
        filterset_class = _find_class(filtersets_module, "CircuitServiceFilterSet")
        _find_meta_tuple(filterset_class, "is_external_business")

        serializers_module = _parse_module(SERIALIZERS_PATH)
        serializer_class = _find_class(serializers_module, "CircuitServiceSerializer")
        _find_meta_tuple(serializer_class, "is_external_business")

        tables_module = _parse_module(TABLES_PATH)
        table_class = _find_class(tables_module, "CircuitServiceTable")
        _find_meta_tuple(table_class, "is_external_business")
        _find_meta_tuple(table_class, "is_external_business", attr_name="default_columns")


class CircuitServiceBusinessCategorySourceTestCase(unittest.TestCase):
    def test_model_declares_business_category_choices_and_field(self) -> None:
        module = _parse_module(MODELS_PATH)

        choices_class = _find_class(module, "BusinessCategoryChoices")
        choices_value = _find_assignment(choices_class, "CHOICES")
        self.assertIsInstance(choices_value, (ast.List, ast.Tuple))

        labels = []
        for choice in choices_value.elts:
            self.assertIsInstance(choice, ast.Tuple)
            self.assertGreaterEqual(len(choice.elts), 2)
            label_node = choice.elts[1]
            self.assertIsInstance(label_node, ast.Constant)
            labels.append(label_node.value)

        self.assertEqual(
            labels,
            [
                "部省传输",
                "商业其他",
                "海事业务",
                "路网业务",
                "老锐捷业务",
                "航信",
                "金航",
                "缆讯",
                "商业百G",
                "长航",
            ],
        )

        class_node = _find_class(module, "CircuitService")
        value = _find_assignment(class_node, "business_category")

        self.assertIsInstance(value, ast.Call)
        self.assertIsInstance(value.func, ast.Attribute)
        self.assertEqual(value.func.attr, "CharField")

        keyword_names = {kw.arg for kw in value.keywords}
        self.assertIn("choices", keyword_names)
        self.assertIn("blank", keyword_names)
        self.assertIn("verbose_name", keyword_names)

        choices_kw = next(kw for kw in value.keywords if kw.arg == "choices")
        blank_kw = next(kw for kw in value.keywords if kw.arg == "blank")
        verbose_kw = next(kw for kw in value.keywords if kw.arg == "verbose_name")

        self.assertIsInstance(choices_kw.value, ast.Name)
        self.assertEqual(choices_kw.value.id, "BusinessCategoryChoices")
        self.assertIs(blank_kw.value.value, True)
        self.assertEqual(verbose_kw.value.value, "业务门类")

    def test_forms_include_business_category_field(self) -> None:
        module = _parse_module(FORMS_PATH)

        for class_name in ("CircuitServiceForm", "CircuitServiceImportForm"):
            class_node = _find_class(module, class_name)
            _find_meta_tuple(class_node, "business_category")

        bulk_edit_class = _find_class(module, "CircuitServiceBulkEditForm")
        _find_assignment(bulk_edit_class, "business_category")

        filter_form_class = _find_class(module, "CircuitServiceFilterForm")
        _find_assignment(filter_form_class, "business_category")

    def test_filterset_serializer_and_table_include_business_category(self) -> None:
        filtersets_module = _parse_module(FILTERSETS_PATH)
        filterset_class = _find_class(filtersets_module, "CircuitServiceFilterSet")
        _find_meta_tuple(filterset_class, "business_category")

        serializers_module = _parse_module(SERIALIZERS_PATH)
        serializer_class = _find_class(serializers_module, "CircuitServiceSerializer")
        _find_meta_tuple(serializer_class, "business_category")

        tables_module = _parse_module(TABLES_PATH)
        table_class = _find_class(tables_module, "CircuitServiceTable")
        _find_meta_tuple(table_class, "business_category")
        _find_meta_tuple(table_class, "business_category", attr_name="default_columns")


class CircuitServiceServiceGroupHierarchySourceTestCase(unittest.TestCase):
    def test_service_group_choices_follow_new_hierarchy(self) -> None:
        module = _parse_module(MODELS_PATH)

        choices_class = _find_class(module, "ServiceGroupChoices")
        choices_value = _find_assignment(choices_class, "CHOICES")
        self.assertIsInstance(choices_value, (ast.List, ast.Tuple))

        labels = []
        for choice in choices_value.elts:
            self.assertIsInstance(choice, ast.Tuple)
            self.assertGreaterEqual(len(choice.elts), 2)
            label_node = choice.elts[1]
            self.assertIsInstance(label_node, ast.Constant)
            labels.append(label_node.value)

        self.assertEqual(
            labels,
            [
                "部省主线",
                "北京城域网",
                "行业专网",
                "行业服务",
                "交通行业",
                "市场",
                "金融专线",
                "海事核心网",
                "海事一体化运维",
                "海事其他",
                "ETC部省",
                "ETC部站",
                "ETC双活",
                "行业专网锐捷",
                "航信生产",
                "航信办公",
                "航信嘉兴上海",
                "金航核心",
                "金航汇聚",
                "金航备线",
                "金航其他",
                "缆讯100G",
                "缆讯组网-10G",
                "缆讯组网-百G",
                "金山",
                "长航业务",
                "长航备线",
            ],
        )

    def test_service_group_category_map_covers_each_group(self) -> None:
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "CircuitService")
        value = _find_assignment(class_node, "SERVICE_GROUP_CATEGORY_MAP")

        self.assertIsInstance(value, ast.Dict)

        keys = []
        values = []
        for key_node, value_node in zip(value.keys, value.values):
            self.assertIsInstance(key_node, ast.Attribute)
            self.assertIsInstance(value_node, ast.Attribute)
            self.assertEqual(key_node.value.id, "ServiceGroupChoices")
            self.assertEqual(value_node.value.id, "BusinessCategoryChoices")
            keys.append(key_node.attr)
            values.append(value_node.attr)

        self.assertEqual(
            keys,
            [
                "MINISTRY_BACKBONE",
                "BEIJING_METRO",
                "INDUSTRY_NETWORK",
                "INDUSTRY_SERVICE",
                "TRANSPORT_INDUSTRY",
                "MARKET",
                "FINANCE_LINE",
                "MARITIME_CORE",
                "MARITIME_INTEGRATED_OM",
                "MARITIME_OTHER",
                "ETC_MINISTRY_PROVINCE",
                "ETC_STATION",
                "ETC_DUAL_ACTIVE",
                "INDUSTRY_NETWORK_RUIJIE",
                "TRAVELSKY_PRODUCTION",
                "TRAVELSKY_OFFICE",
                "TRAVELSKY_JIAXING_SHANGHAI",
                "JINHANG_CORE",
                "JINHANG_AGGREGATION",
                "JINHANG_BACKUP",
                "JINHANG_OTHER",
                "LANXUN_100G",
                "LANXUN_NETWORK_10G",
                "LANXUN_NETWORK_100G",
                "JINSHAN",
                "CHANGHANG_SERVICE",
                "CHANGHANG_BACKUP",
            ],
        )
        self.assertEqual(
            values,
            [
                "MINISTRY_PROVINCE_TRANSPORT",
                "MINISTRY_PROVINCE_TRANSPORT",
                "MINISTRY_PROVINCE_TRANSPORT",
                "MINISTRY_PROVINCE_TRANSPORT",
                "MINISTRY_PROVINCE_TRANSPORT",
                "COMMERCIAL_OTHER",
                "COMMERCIAL_OTHER",
                "MARITIME_SERVICE",
                "MARITIME_SERVICE",
                "MARITIME_SERVICE",
                "ROAD_NETWORK_SERVICE",
                "ROAD_NETWORK_SERVICE",
                "ROAD_NETWORK_SERVICE",
                "LEGACY_RUIJIE_SERVICE",
                "TRAVELSKY",
                "TRAVELSKY",
                "TRAVELSKY",
                "JINHANG",
                "JINHANG",
                "JINHANG",
                "JINHANG",
                "LANXUN",
                "LANXUN",
                "LANXUN",
                "COMMERCIAL_100G",
                "CHANGHANG",
                "CHANGHANG",
            ],
        )

    def test_edit_form_and_template_include_cascading_behavior(self) -> None:
        forms_text = FORMS_PATH.read_text(encoding="utf-8-sig")
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("data-service-group-category-map", forms_text)
        self.assertIn("data-placeholder", forms_text)
        self.assertIn("id_business_category", template_text)
        self.assertIn("id_service_group", template_text)
        self.assertIn("data-service-group-category-map", template_text)


class CircuitServiceSpecialLineNameSourceTestCase(unittest.TestCase):
    def test_special_line_name_is_primary_display_field(self) -> None:
        models_module = _parse_module(MODELS_PATH)
        class_node = _find_class(models_module, "CircuitService")

        meta_class = _find_class(ast.Module(body=class_node.body, type_ignores=[]), "Meta")
        ordering_value = _find_assignment(meta_class, "ordering")
        self.assertIsInstance(ordering_value, (ast.Tuple, ast.List))
        ordering_items = [elt.value for elt in ordering_value.elts if isinstance(elt, ast.Constant)]
        self.assertIn("special_line_name", ordering_items)

        models_text = MODELS_PATH.read_text(encoding="utf-8-sig")
        self.assertIn("def __str__(self):", models_text)
        self.assertIn("self.get_service_group_display()", models_text)
        self.assertIn("self.special_line_name", models_text)
        self.assertIn(" / ", models_text)

        tables_module = _parse_module(TABLES_PATH)
        table_class = _find_class(tables_module, "CircuitServiceTable")
        primary_column = _find_assignment(table_class, "special_line_name")
        self.assertIsInstance(primary_column, ast.Call)
        linkify_kw = next(kw for kw in primary_column.keywords if kw.arg == "linkify")
        verbose_kw = next(kw for kw in primary_column.keywords if kw.arg == "verbose_name")
        self.assertIs(linkify_kw.value.value, True)
        self.assertEqual(verbose_kw.value.value, "专线名称")

        _find_meta_tuple(table_class, "special_line_name", attr_name="default_columns")
        tables_text = TABLES_PATH.read_text(encoding="utf-8-sig")
        self.assertIn("str(record.circuit_service)", tables_text)

    def test_name_field_uses_circuit_number_label(self) -> None:
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "CircuitService")
        value = _find_assignment(class_node, "name")

        self.assertIsInstance(value, ast.Call)
        verbose_kw = next(kw for kw in value.keywords if kw.arg == "verbose_name")
        self.assertEqual(verbose_kw.value.value, "电路编号")

        tables_module = _parse_module(TABLES_PATH)
        table_class = _find_class(tables_module, "CircuitServiceTable")
        column_value = _find_assignment(table_class, "name")
        self.assertIsInstance(column_value, ast.Call)
        table_verbose_kw = next(kw for kw in column_value.keywords if kw.arg == "verbose_name")
        self.assertEqual(table_verbose_kw.value.value, "电路编号")

    def test_model_declares_required_special_line_name_field(self) -> None:
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "CircuitService")
        value = _find_assignment(class_node, "special_line_name")

        self.assertIsInstance(value, ast.Call)
        self.assertIsInstance(value.func, ast.Attribute)
        self.assertEqual(value.func.attr, "CharField")

        keyword_names = {kw.arg for kw in value.keywords}
        self.assertIn("max_length", keyword_names)
        self.assertIn("verbose_name", keyword_names)
        self.assertNotIn("blank", keyword_names)

        max_length_kw = next(kw for kw in value.keywords if kw.arg == "max_length")
        verbose_kw = next(kw for kw in value.keywords if kw.arg == "verbose_name")
        self.assertEqual(max_length_kw.value.value, 100)
        self.assertEqual(verbose_kw.value.value, "专线名称")

    def test_forms_serializer_and_table_include_special_line_name(self) -> None:
        forms_module = _parse_module(FORMS_PATH)
        form_class = _find_class(forms_module, "CircuitServiceForm")
        _find_meta_tuple(form_class, "special_line_name")
        fieldsets_value = _find_assignment(form_class, "fieldsets")
        self.assertIsInstance(fieldsets_value, ast.Tuple)
        first_fieldset = fieldsets_value.elts[0]
        self.assertIsInstance(first_fieldset, ast.Call)
        fieldset_items = [
            arg.value for arg in first_fieldset.args
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
        ]
        self.assertEqual(fieldset_items[0], "special_line_name")

        import_form_class = _find_class(forms_module, "CircuitServiceImportForm")
        _find_meta_tuple(import_form_class, "special_line_name")

        filtersets_module = _parse_module(FILTERSETS_PATH)
        filterset_class = _find_class(filtersets_module, "CircuitServiceFilterSet")
        _find_meta_tuple(filterset_class, "special_line_name")

        serializers_module = _parse_module(SERIALIZERS_PATH)
        serializer_class = _find_class(serializers_module, "CircuitServiceSerializer")
        _find_meta_tuple(serializer_class, "special_line_name")

        tables_module = _parse_module(TABLES_PATH)
        table_class = _find_class(tables_module, "CircuitServiceTable")
        _find_meta_tuple(table_class, "special_line_name")
        _find_meta_tuple(table_class, "special_line_name", attr_name="default_columns")


if __name__ == "__main__":
    unittest.main()
