from __future__ import annotations

import re
from datetime import date
from typing import Any

from .schema import find_join_path


MONTHLY_DEPARTMENT_LEARNING_REPORT = "department_monthly_per_capita_learning_hours"


def detect_kpi_report(
    question: str,
    normalized_text: str,
    catalog: dict[str, Any],
    today: date,
) -> dict[str, Any] | None:
    """Recognize audited KPI reports whose business grain cannot be guessed by SVM."""
    has_department = "部门" in normalized_text
    has_month = any(
        word in normalized_text
        for word in (
            "月份",
            "每月",
            "每个月",
            "逐月",
            "月度",
            "按月",
            "一至十二月",
            "一到十二月",
            "1至12月",
            "1到12月",
            "十二个月",
        )
    )
    has_per_capita = any(
        word in normalized_text
        for word in (
            "人均",
            "平均每人",
            "每人平均",
            "每位员工平均",
            "平均每位员工",
            "员工平均",
            "员工人均",
        )
    )
    has_learning_duration = any(
        word in normalized_text
        for word in (
            "学习时长",
            "学习时间",
            "学习用时",
            "培训时长",
            "培训学时",
            "课程学时",
            "学习小时",
        )
    )
    if not all((has_department, has_month, has_per_capita, has_learning_duration)):
        return None

    year_match = re.search(r"(20\d{2})(?:年度|全年|年)", normalized_text)
    if year_match:
        year = int(year_match.group(1))
        expression = year_match.group(0)
    elif "今年" in normalized_text:
        year = today.year
        expression = "今年"
    elif "去年" in normalized_text:
        year = today.year - 1
        expression = "去年"
    else:
        raise ValueError("已识别为部门逐月人均学习时长报表，但缺少明确年度")
    return build_monthly_department_learning_plan(question, year, catalog, expression)


def build_monthly_department_learning_plan(
    question: str,
    year: int,
    catalog: dict[str, Any],
    time_expression: str | None = None,
) -> dict[str, Any]:
    if year < 2000 or year > 2100:
        raise ValueError(f"报表年度超出允许范围: {year}")
    path = find_join_path(
        catalog, "Student_Course_Log", "Student_Info", max_hops=1
    )
    if path is None or len(path) != 1:
        raise ValueError("学习日志到学员表的审核关联不存在")
    return {
        "question": question,
        "report_type": MONTHLY_DEPARTMENT_LEARNING_REPORT,
        "intent": "cross_tab",
        "domain": "training",
        "table": "Student_Course_Log",
        "metric_column": None,
        "metric_table": "Student_Course_Log",
        "metric_expression": "SUM(DATEDIFF(SECOND, BeginTime, EndTime)) / active_students / 3600",
        "metric_unit": "hour",
        "dimension_column": "Department",
        "dimension_table": "Student_Info",
        "secondary_dimension": "MONTH(Student_Course_Log.BeginTime)",
        "aggregation": "per_capita_hours",
        "filters": [
            {
                "table": "Student_Info",
                "field": "Status",
                "operator": "=",
                "value": 1,
                "meaning": "仅启用学员进入人均分母",
            }
        ],
        "joins": path,
        "entities": [],
        "unresolved_entities": [],
        "time_field": "BeginTime",
        "date_start": date(year, 1, 1).isoformat(),
        "date_end": date(year + 1, 1, 1).isoformat(),
        "time_expression": time_expression or f"{year}年度",
        "limit": None,
        "order": "asc",
        "confidence": {
            "intent": 1.0,
            "domain": 1.0,
            "table": 1.0,
            "aggregation": 1.0,
        },
        "sources": {"table": "audited_kpi_rule", "metric": "audited_kpi_rule"},
        "warnings": [
            "人均口径：Status=1的启用学员为分母，有效课程学习会话时长合计为分子，单位小时",
            "设计书没有部门与在职状态历史表，历史学习记录按学员当前部门归属，各月分母使用当前启用学员数",
            "跨月学习会话按BeginTime归入开始月份",
            "当前采用Student_Course_Log；若生产报表以课件日志为官方口径，需要调整KPI规则",
        ],
    }


def reject_unsupported_analytics(normalized_text: str) -> None:
    """Refuse advanced analytics instead of returning a plausible but wrong count."""
    markers = (
        "同比",
        "环比",
        "中位数",
        "百分位",
        "占比",
        "转化率",
        "横向对比",
        "交叉表",
        "透视表",
    )
    if any(marker in normalized_text for marker in markers) or "人均" in normalized_text:
        raise ValueError(
            "这是复合分析/报表口径，当前没有匹配到已审核的KPI规则；为避免生成错误SQL，已拒绝退化为普通计数查询"
        )
