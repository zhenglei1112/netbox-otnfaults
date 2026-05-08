from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = ROOT / "netbox_otnfaults" / "forms.py"
TEMPLATE_PATH = ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfaultimpact.html"
FILTERSETS_PATH = ROOT / "netbox_otnfaults" / "filtersets.py"
SERIALIZERS_PATH = ROOT / "netbox_otnfaults" / "api" / "serializers.py"
TABLES_PATH = ROOT / "netbox_otnfaults" / "tables.py"


class OtnFaultImpactBusinessImpactSourceTestCase(unittest.TestCase):
    def test_model_defines_business_impact_choice_field(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8")
        self.assertIn("class BusinessImpactChoices(ChoiceSet):", source)
        self.assertIn("INTERRUPTED = 'interrupted'", source)
        self.assertIn("NOT_INTERRUPTED = 'not_interrupted'", source)
        self.assertIn("(INTERRUPTED, '业务中断', 'red')", source)
        self.assertIn("(NOT_INTERRUPTED, '业务未中断', 'blue')", source)
        self.assertIn("def get_business_impact_color(self):", source)
        self.assertIn("return BusinessImpactChoices.colors.get(self.business_impact)", source)

        impact_model = source.split("class OtnFaultImpact", 1)[1].split("class Meta:", 1)[0]
        self.assertIn("business_impact = models.CharField(", impact_model)
        self.assertIn("choices=BusinessImpactChoices", impact_model)
        self.assertIn("verbose_name='业务影响'", impact_model)

        self.assertLess(
            impact_model.index("business_impact = models.CharField("),
            impact_model.index("service_interruption_time = models.DateTimeField("),
        )

    def test_edit_form_places_business_impact_before_business_fault_time(self) -> None:
        source = FORMS_PATH.read_text(encoding="utf-8")
        form_block = source.split("class OtnFaultImpactForm", 1)[1].split("class OtnFaultImpactBulkEditForm", 1)[0]
        fields_block = form_block.split("fields = (", 1)[1].split(")", 1)[0]

        self.assertIn("'business_impact'", fields_block)
        self.assertLess(
            fields_block.index("'business_impact'"),
            fields_block.index("'service_interruption_time'"),
        )

    def test_detail_template_places_business_impact_before_business_fault_time(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("{% load i18n helpers %}", template)
        self.assertIn("<th scope=\"row\">业务影响</th>", template)
        self.assertIn("{% badge object.get_business_impact_display bg_color=object.get_business_impact_color %}", template)
        self.assertLess(
            template.index("<th scope=\"row\">业务影响</th>"),
            template.index("<th scope=\"row\">业务故障时间</th>"),
        )

    def test_list_tables_render_business_impact_as_choice_flag(self) -> None:
        tables = TABLES_PATH.read_text(encoding="utf-8")
        impact_table = tables.split("class OtnFaultImpactTable", 1)[1].split("class OtnFaultImpactDetailTable", 1)[0]
        detail_table = tables.split("class OtnFaultImpactDetailTable", 1)[1].split("class OtnFaultImpactSummaryTable", 1)[0]

        self.assertIn("business_impact = columns.ChoiceFieldColumn(", impact_table)
        self.assertIn("business_impact = columns.ChoiceFieldColumn(", detail_table)

    def test_filterset_and_serializer_expose_business_impact(self) -> None:
        filtersets = FILTERSETS_PATH.read_text(encoding="utf-8")
        impact_filterset = filtersets.split("class OtnFaultImpactFilterSet", 1)[1].split("class OtnPathFilterSet", 1)[0]
        self.assertIn("'business_impact'", impact_filterset)

        serializers = SERIALIZERS_PATH.read_text(encoding="utf-8")
        impact_serializer = serializers.split("class OtnFaultImpactSerializer", 1)[1].split("class NestedOtnPathGroupSerializer", 1)[0]
        self.assertIn("'business_impact'", impact_serializer)
        self.assertLess(
            impact_serializer.index("'business_impact'"),
            impact_serializer.index("'service_interruption_time'"),
        )

    def test_fault_detail_impact_summary_keeps_actions_column_last(self) -> None:
        tables = TABLES_PATH.read_text(encoding="utf-8")
        summary_table = tables.split("class OtnFaultImpactSummaryTable", 1)[1].split("class OtnPathTable", 1)[0]
        fields_block = summary_table.split("fields = (", 1)[1].split(")", 1)[0]
        default_columns_block = summary_table.split("default_columns = (", 1)[1].split(")", 1)[0]

        self.assertIn("'business_impact'", fields_block)
        self.assertLess(fields_block.index("'secondary_faults'"), fields_block.index("'business_impact'"))
        self.assertLess(fields_block.index("'business_impact'"), fields_block.index("'actions'"))
        fields = [item.strip() for item in fields_block.split(",") if item.strip()]
        self.assertEqual("'actions'", fields[-1])

        self.assertIn("'business_impact'", default_columns_block)
        self.assertLess(
            default_columns_block.index("'secondary_faults'"),
            default_columns_block.index("'business_impact'"),
        )


if __name__ == "__main__":
    unittest.main()
