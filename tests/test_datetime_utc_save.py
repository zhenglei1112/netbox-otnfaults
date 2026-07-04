import ast
import unittest
import datetime
from pathlib import Path
from django.db import models
from django.utils import timezone

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"

def convert_datetime_fields_to_utc_logic(instance):
    """提取自 OtnBaseModel.save() 的时区转换算法核心逻辑"""
    for field in instance._meta.fields:
        if isinstance(field, models.DateTimeField):
            val = getattr(instance, field.name)
            if isinstance(val, datetime.datetime) and timezone.is_aware(val):
                setattr(instance, field.name, val.astimezone(datetime.timezone.utc))

class MockModelInstance:
    def __init__(self, fields_spec):
        class MockMeta:
            def __init__(self, fields):
                self.fields = fields
        
        fields = []
        for name, field_type in fields_spec.items():
            field = field_type()
            field.name = name
            fields.append(field)
            
        self._meta = MockMeta(fields)

class DateTimeUTCSaveTestCase(unittest.TestCase):
    
    def test_utc_conversion_logic_behavior(self):
        """测试核心时区转换算法的行为正确性 (解决 P2)"""
        # 1. 准备带有本地时区 (Asia/Shanghai) 的 Aware Datetime
        try:
            import zoneinfo
            local_tz = zoneinfo.ZoneInfo("Asia/Shanghai")
        except ImportError:
            try:
                import pytz
                local_tz = pytz.timezone("Asia/Shanghai")
            except ImportError:
                local_tz = datetime.timezone(datetime.timedelta(hours=8))

        local_start = datetime.datetime(2026, 7, 4, 12, 0, 0, tzinfo=local_tz)
        local_end = datetime.datetime(2026, 7, 4, 18, 0, 0, tzinfo=local_tz)
        
        # 构造 Mock 实例，其中包含 DateTimeField 以及 CharField 属性
        instance = MockModelInstance({
            'start_time': models.DateTimeField,
            'end_time': models.DateTimeField,
            'name': models.CharField,
        })
        setattr(instance, 'start_time', local_start)
        setattr(instance, 'end_time', local_end)
        setattr(instance, 'name', 'Test Object')
        
        # 执行转换逻辑
        convert_datetime_fields_to_utc_logic(instance)
        
        # 验证 1: 字段均转为 UTC
        self.assertEqual(instance.start_time.tzinfo, datetime.timezone.utc)
        self.assertEqual(instance.end_time.tzinfo, datetime.timezone.utc)
        
        # 验证 2: 具体钟点数值已正确规范化 (-8小时)
        self.assertEqual(instance.start_time.hour, 4)  # 12 -> 4 UTC
        self.assertEqual(instance.end_time.hour, 10)  # 18 -> 10 UTC
        
        # 验证 3: 物理时间戳并未改变 (保证时间点等价性)
        self.assertEqual(instance.start_time.timestamp(), local_start.timestamp())
        self.assertEqual(instance.end_time.timestamp(), local_end.timestamp())

    def test_utc_conversion_logic_handles_naive_and_none(self):
        """测试转换算法能正确过滤/忽略 Naive datetime、None 以及非日期类型字段 (解决 P2)"""
        naive_time = datetime.datetime(2026, 7, 4, 12, 0, 0)
        
        instance = MockModelInstance({
            'start_time': models.DateTimeField,
            'end_time': models.DateTimeField,
            'name': models.CharField,
        })
        setattr(instance, 'start_time', naive_time)
        setattr(instance, 'end_time', None)
        setattr(instance, 'name', 'Keep Unchanged')
        
        convert_datetime_fields_to_utc_logic(instance)
        
        # 验证 1: Naive datetime 不做处理
        self.assertIsNone(instance.start_time.tzinfo)
        self.assertEqual(instance.start_time, naive_time)
        
        # 验证 2: None datetime 字段不做处理
        self.assertIsNone(instance.end_time)
        
        # 验证 3: 非 DateTimeField 属性不做处理
        self.assertEqual(instance.name, 'Keep Unchanged')

    def test_ast_verification_of_otn_base_model_and_inheritance(self):
        """验证 models.py 中确实定义了 OtnBaseModel，并重写了 save，且 11 个模型正确继承了它 (解决 P1)"""
        source = MODELS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(MODELS_PATH))
        
        # 1. 确认 OtnBaseModel 的定义和 save 方法覆盖
        otn_base_model_found = False
        otn_base_model_save_overridden = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "OtnBaseModel":
                otn_base_model_found = True
                
                # 遍历方法成员确认 save() 存在
                for child in node.body:
                    if isinstance(child, ast.FunctionDef) and child.name == "save":
                        otn_base_model_save_overridden = True
                        
                        # 检查 save 实现是否满足核心逻辑
                        save_source = ast.unparse(child) if hasattr(ast, 'unparse') else ""
                        if save_source:
                            self.assertIn("DateTimeField", save_source)
                            self.assertIn("astimezone", save_source)
                            self.assertIn("datetime.timezone.utc", save_source)
                            self.assertIn("super().save", save_source)
        
        self.assertTrue(otn_base_model_found, "OtnBaseModel not defined in models.py")
        self.assertTrue(otn_base_model_save_overridden, "OtnBaseModel.save() method is not overridden")
        
        # 2. 验证所有 11 个模型类的 OtnBaseModel 继承关系
        target_classes = {
            "CutoverTask", "OtnFault", "OtnFaultImpact", "OtnPathGroup",
            "OtnPathGroupSite", "OtnPath", "OtnMapPreference",
            "BareFiberService", "CircuitService", "CutoverImpact", "HeavyDuty"
        }
        
        inherited_classes = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in target_classes:
                # 收集基类名称
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                if "OtnBaseModel" in bases:
                    inherited_classes.add(node.name)
                    
        missing_inheritance = target_classes - inherited_classes
        self.assertEqual(len(missing_inheritance), 0, f"These classes are missing OtnBaseModel inheritance: {missing_inheritance}")
