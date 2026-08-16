from __future__ import annotations

import copy
import json
import unittest
from datetime import date, timedelta

import pandas as pd

from nl2sql_ml.compiler import SQLCompiler, SQLCompileError
from nl2sql_ml.engine import NL2SQLEngine
from nl2sql_ml.evaluation import evaluate_acceptance
from nl2sql_ml.model import ModelBundle
from nl2sql_ml.schema import load_catalog, load_semantic_layer, project_root, schema_fingerprint
from tools.run_adversarial_200 import validate as validate_adversarial_case


class SystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = project_root()
        cls.catalog = load_catalog()
        cls.semantic_layer = load_semantic_layer()
        cls.engine = NL2SQLEngine()

    def test_design_book_schema_is_complete(self) -> None:
        self.assertEqual(len(self.catalog["domains"]), 12)
        self.assertEqual(len(self.catalog["tables"]), 111)
        self.assertEqual(sum(len(t["fields"]) for t in self.catalog["tables"]), 1088)
        self.assertEqual(len(self.catalog["relations"]), 48)
        self.assertEqual(len(self.catalog["query_joins"]), 89)
        self.assertIn("exam_score", self.semantic_layer["facts"])

    def test_global_serial_number_rule_is_applied(self) -> None:
        for table in self.catalog["tables"]:
            serial = next(field for field in table["fields"] if field["name"].lower() == "serialno")
            self.assertEqual(serial["type"], "bigint", table["name"])
            self.assertEqual(serial["default"], "IDENTITY", table["name"])

    def test_dataset_covers_every_table(self) -> None:
        frame = pd.read_json(self.root / "data" / "dataset.jsonl", lines=True)
        self.assertEqual(len(frame), 72000)
        self.assertEqual(frame["question"].nunique(), 72000)
        self.assertEqual(set(frame["table"]), {table["name"] for table in self.catalog["tables"]})
        self.assertGreaterEqual(int(frame["table"].value_counts().min()), 540)
        self.assertGreater(int(frame["plan"].map(lambda plan: bool(plan.get("joins"))).sum()), 5000)
        self.assertGreater(int(frame["plan"].map(lambda plan: len(plan.get("filters", [])) >= 2).sum()), 5000)
        self.assertEqual(
            int(frame["plan"].map(lambda plan: plan.get("report_type") == "department_monthly_per_capita_learning_hours").sum()),
            4000,
        )
        self.assertEqual(
            int(frame["plan"].map(lambda plan: plan.get("report_type") == "student_exam_score_aggregate").sum()),
            4000,
        )
        self.assertEqual(
            int(frame["plan"].map(lambda plan: plan.get("report_type") == "student_exam_score_ranking").sum()),
            4000,
        )

    def test_all_curated_acceptance_queries_pass(self) -> None:
        result = evaluate_acceptance(
            self.engine,
            self.root / "data" / "acceptance.jsonl",
            self.root / "data" / "dataset.jsonl",
        )
        self.assertEqual(result["cases"], 82)
        self.assertEqual(result["passed"], 82)
        self.assertEqual(result["schema_coverage"]["coverage"], 1.0)

    def test_adversarial_200_queries_pass(self) -> None:
        cases = [
            json.loads(line)
            for line in (self.root / "data" / "adversarial_200.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(cases), 200)
        for case in cases:
            with self.subTest(case=case["id"], question=case["question"]):
                detail = validate_adversarial_case(case, self.engine)
                self.assertEqual(detail["status"], "passed")

    def test_person_filter_adds_qualified_join(self) -> None:
        result = self.engine.translate("查询张三所有的考试报名记录")
        plan = result["plan"]
        self.assertEqual(plan["table"], "Exam_Apply")
        self.assertEqual(len(plan["joins"]), 1)
        self.assertIn(
            {"table": "Student_Info", "field": "ActualName", "operator": "=", "value": "张三", "entity_type": "person_name"},
            plan["filters"],
        )
        self.assertIn("INNER JOIN [Student_Info]", result["sql"])
        self.assertIn("[t1].[ActualName] = ?", result["sql"])
        self.assertEqual(result["params"], ["张三"])

    def test_two_hop_exam_score_person_filter(self) -> None:
        result = self.engine.translate("查询李四的考试成绩")
        self.assertEqual(result["plan"]["table"], "clerk_kscj")
        self.assertEqual(len(result["plan"]["joins"]), 2)
        self.assertIn("[Student_Info]", result["sql"])
        self.assertEqual(result["params"], ["李四"])

    def test_remote_dimension_grouping(self) -> None:
        result = self.engine.translate("按部门统计考试报名数量")
        self.assertEqual(result["plan"]["table"], "Exam_Apply")
        self.assertEqual(result["plan"]["dimension_table"], "Student_Info")
        self.assertEqual(result["plan"]["dimension_column"], "Department")
        self.assertIn("GROUP BY [t1].[Department]", result["sql"])

    def test_multiple_filters_and_date_range(self) -> None:
        result = self.engine.translate("查询本月张三状态为1的考试报名记录")
        today = date.today()
        month_start = today.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        self.assertEqual(result["params"], [1, "张三", month_start.isoformat(), next_month.isoformat()])
        self.assertIn("[t0].[Status] = ?", result["sql"])
        self.assertIn("[t1].[ActualName] = ?", result["sql"])
        self.assertIn("[t0].[CreateTime] >= ?", result["sql"])

    def test_unsafe_role_entity_is_not_silently_dropped(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.translate("查询张三创建的课程")

    def test_department_monthly_per_capita_learning_report(self) -> None:
        result = self.engine.translate("2026年度各部门一至十二月份人均学习时长横向对比")
        plan = result["plan"]
        self.assertEqual(plan["report_type"], "department_monthly_per_capita_learning_hours")
        self.assertEqual(plan["intent"], "cross_tab")
        self.assertEqual(plan["table"], "Student_Course_Log")
        self.assertEqual(plan["date_start"], "2026-01-01")
        self.assertEqual(plan["date_end"], "2027-01-01")
        self.assertEqual(result["params"], ["2026-01-01", "2027-01-01", 1])
        self.assertIn("LEFT JOIN [Student_Course_Log]", result["sql"])
        self.assertIn("COUNT(DISTINCT [s].[Id])", result["sql"])
        self.assertIn("[1月人均学习时长_小时]", result["sql"])
        self.assertIn("[12月人均学习时长_小时]", result["sql"])

    def test_monthly_learning_report_paraphrases(self) -> None:
        questions = (
            "2025年不同部门每个月平均每人培训学时趋势报表",
            "各部门2024全年逐月员工人均课程学习时间对比表",
            "2023年度按部门月度每人平均学习用时汇总",
        )
        for question in questions:
            with self.subTest(question=question):
                result = self.engine.translate(question)
                self.assertEqual(result["plan"]["report_type"], "department_monthly_per_capita_learning_hours")

    def test_unsupported_advanced_analytics_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "已审核的KPI规则"):
            self.engine.translate("2026年度各部门每月学习时长中位数对比")

    def test_compositional_exam_score_query(self) -> None:
        result = self.engine.translate("2026年张三和李四各自在线性代数中取得的最高分")
        plan = result["plan"]
        self.assertEqual(plan["report_type"], "student_exam_score_aggregate")
        self.assertEqual(plan["fact"], "exam_score")
        self.assertEqual(plan["aggregation"], "max")
        self.assertEqual(
            plan["semantic_ast"]["filters"]["student_name"]["values"],
            ["张三", "李四"],
        )
        self.assertEqual(
            result["params"],
            ["张三", "李四", "线性代数", "2026-01-01", "2027-01-01", 1],
        )
        self.assertIn("MAX([k].[Cj])", result["sql"])
        self.assertIn("[s].[ActualName] IN (?, ?)", result["sql"])
        self.assertIn("CONVERT(varchar(50), [p].[SiteID]) = [c].[Id]", result["sql"])

    def test_compositional_exam_score_paraphrases(self) -> None:
        cases = {
            "查询2025年度王五与赵敏分别在高等数学课程中的最低成绩": ("min", ["王五", "赵敏"]),
            "统计张三、李四以及王五各人2024全年在课程名称为数据分析的考试中的平均分": ("avg", ["张三", "李四", "王五"]),
            "2026年张三和李四各自最高分": ("max", ["张三", "李四"]),
        }
        for question, (aggregation, people) in cases.items():
            with self.subTest(question=question):
                plan = self.engine.translate(question)["plan"]
                self.assertEqual(plan["aggregation"], aggregation)
                self.assertEqual(plan["semantic_ast"]["filters"]["student_name"]["values"], people)

    def test_ambiguous_multi_person_score_query_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "分别统计还是合并统计"):
            self.engine.translate("2026年张三和李四在线性代数中的最高分")

    def test_low_confidence_table_prediction_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "目标事实表无法可靠识别"):
            self.engine.translate("查询量子涨落熵系数")

    def test_exam_score_student_ranking(self) -> None:
        result = self.engine.translate("2026年研发部所有课程平均成绩最高的10个学生")
        plan = result["plan"]
        self.assertEqual(plan["report_type"], "student_exam_score_ranking")
        self.assertEqual(plan["aggregation"], "avg")
        self.assertEqual(plan["limit"], 10)
        self.assertEqual(plan["semantic_ast"]["filters"]["department"], "研发部")
        self.assertEqual(plan["semantic_ast"]["filters"]["course_scope"], "all_courses")
        self.assertTrue(result["sql"].startswith("SELECT TOP (10)"))
        self.assertIn("AVG([k].[Cj]) AS [avg_score]", result["sql"])
        self.assertIn("[s].[Department] = ?", result["sql"])
        self.assertIn("ORDER BY [avg_score] DESC", result["sql"])
        self.assertEqual(result["params"], ["研发部", "2026-01-01", "2027-01-01", 1])

    def test_student_major_score_ranking_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Student_Info学员表没有专业字段"):
            self.engine.translate("2026年数学专业所有课程平均成绩最高的10个学生")

    def test_explicit_calendar_year_filter(self) -> None:
        result = self.engine.translate("查询2026年度考试报名记录")
        self.assertEqual(result["plan"]["table"], "Exam_Apply")
        self.assertEqual(result["plan"]["time_field"], "CreateTime")
        self.assertEqual(result["params"], ["2026-01-01", "2027-01-01"])

    def test_sql_server_top_n(self) -> None:
        result = self.engine.translate("查询课程学分最高的前5个课程名称")
        self.assertEqual(result["plan"]["table"], "Course_Info")
        self.assertEqual(result["plan"]["metric_column"], "CreditHour")
        self.assertEqual(result["plan"]["dimension_column"], "Name")
        self.assertTrue(result["sql"].startswith("SELECT TOP (5)"))
        self.assertNotIn(" LIMIT ", result["sql"].upper())

    def test_date_filter_uses_half_open_range(self) -> None:
        result = self.engine.translate("查询本月创建的岗位")
        today = date.today()
        month_start = today.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        self.assertEqual(result["params"], [month_start.isoformat(), next_month.isoformat()])
        self.assertIn("[CreateTime] >= ?", result["sql"])
        self.assertIn("[CreateTime] < ?", result["sql"])

    def test_filter_value_is_parameterized(self) -> None:
        compiler = SQLCompiler(self.catalog)
        dangerous = "1'; DROP TABLE Student_Info;--"
        sql, params = compiler.compile(
            {
                "intent": "list",
                "table": "Exam_Apply",
                "filters": [{"field": "Status", "operator": "=", "value": dangerous}],
            }
        )
        self.assertNotIn(dangerous, sql)
        self.assertEqual(params, [dangerous])
        self.assertEqual(sql.count(";"), 1)

    def test_in_filter_is_parameterized(self) -> None:
        compiler = SQLCompiler(self.catalog)
        sql, params = compiler.compile(
            {
                "intent": "list",
                "table": "Student_Info",
                "filters": [
                    {
                        "field": "ActualName",
                        "operator": "IN",
                        "value": ["张三", "李四"],
                    }
                ],
            }
        )
        self.assertIn("[ActualName] IN (?, ?)", sql)
        self.assertEqual(params, ["张三", "李四"])

    def test_compiler_rejects_unknown_identifiers_operators_and_joins(self) -> None:
        compiler = SQLCompiler(self.catalog)
        with self.assertRaises(SQLCompileError):
            compiler.compile({"intent": "list", "table": "not_a_table"})
        with self.assertRaises(SQLCompileError):
            compiler.compile(
                {
                    "intent": "list",
                    "table": "Exam_Apply",
                    "filters": [{"field": "Status", "operator": "; DROP", "value": 1}],
                }
            )
        with self.assertRaises(SQLCompileError):
            compiler.compile(
                {
                    "intent": "list",
                    "table": "Exam_Apply",
                    "joins": [
                        {
                            "left_table": "Exam_Apply",
                            "left_field": "ExamId",
                            "right_table": "Course_Info",
                            "right_field": "Id",
                        }
                    ],
                }
            )

    def test_model_is_bound_to_schema_fingerprint(self) -> None:
        modified = copy.deepcopy(self.catalog)
        modified["tables"][0]["fields"][0]["type"] = "int"
        self.assertNotEqual(schema_fingerprint(modified), schema_fingerprint(self.catalog))
        with self.assertRaises(ValueError):
            ModelBundle(self.root / "artifacts" / "model.joblib", modified)

    def test_model_is_bound_to_semantic_layer_fingerprint(self) -> None:
        modified = copy.deepcopy(self.semantic_layer)
        modified["facts"]["exam_score"]["grain"] = "changed"
        with self.assertRaises(ValueError):
            ModelBundle(
                self.root / "artifacts" / "model.joblib",
                self.catalog,
                modified,
            )


if __name__ == "__main__":
    unittest.main()
