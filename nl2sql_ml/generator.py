from __future__ import annotations

import json
import random
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .compiler import SQLCompiler
from .compositional import build_exam_score_plan, build_exam_score_ranking_plan
from .kpi import build_monthly_department_learning_plan
from .schema import (
    date_fields,
    dimension_fields,
    field_map,
    find_join_path,
    is_numeric,
    is_safe_entity_path,
    join_rule_key,
    load_semantic_layer,
    numeric_fields,
    primary_key,
)


INTENTS = ("list", "count", "aggregate", "group_aggregate", "top_n", "cross_tab")
TIME_PHRASES = (
    ("", None),
    ("今天", "today"),
    ("昨天", "yesterday"),
    ("本月", "this_month"),
    ("上个月", "last_month"),
    ("今年", "this_year"),
    ("去年", "last_year"),
    ("最近7天", "last_7_days"),
    ("近30天", "last_30_days"),
    ("过去90天", "last_90_days"),
)


def generate_dataset(
    catalog: dict[str, Any],
    dictionary: dict[str, Any],
    output_path: str | Path,
    count: int = 72000,
    seed: int = 20260816,
) -> dict[str, Any]:
    if count < len(catalog["tables"]) * 20:
        raise ValueError(f"为覆盖全部表，样本数至少需要 {len(catalog['tables']) * 20}")
    rng = random.Random(seed)
    semantic_layer = load_semantic_layer()
    compiler = SQLCompiler(catalog, semantic_layer)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tables = catalog["tables"]
    intent_counts = {name: 0 for name in INTENTS}
    table_counts = {table["name"]: 0 for table in tables}
    domain_counts: dict[str, int] = {}
    reference = date(2026, 1, 15)
    alias_counts = Counter(
        _normalize_alias(alias)
        for table in tables
        for alias in table.get("aliases", [])
        if _normalize_alias(alias)
    )
    entity_routes = {
        table["name"]: _build_entity_routes(table, catalog, dictionary)
        for table in tables
    }
    complex_counts = {
        "joined_queries": 0,
        "multi_filter_queries": 0,
        "time_filter_queries": 0,
        "remote_dimension_queries": 0,
        "cross_tab_queries": 0,
        "compositional_exam_score_queries": 0,
        "exam_score_ranking_queries": 0,
    }
    seen_questions: set[str] = set()
    available_special = max(0, count - len(tables) * 20)
    desired_each = max(500, count // 18)
    special_total = min(desired_each * 3, available_special)
    monthly_report_count = special_total // 3
    exam_score_count = special_total // 3
    exam_score_ranking_count = special_total - monthly_report_count - exam_score_count
    base_count = count - special_total

    with output.open("w", encoding="utf-8") as handle:
        for index in range(base_count):
            table = tables[index % len(tables)]
            for _ in range(100):
                plan, question = _make_sample(
                    table,
                    catalog,
                    dictionary,
                    rng,
                    reference,
                    alias_counts,
                    entity_routes[table["name"]],
                )
                if question not in seen_questions:
                    seen_questions.add(question)
                    break
            else:
                raise RuntimeError(
                    f"无法为 {table['name']} 继续生成不重复问句；请扩充该表的模板或字段别名"
                )
            sql, params = compiler.compile(plan)
            record = {
                "id": index,
                "question": question,
                "intent": plan["intent"],
                "domain": table["domain"],
                "table": table["name"],
                "aggregation": plan.get("aggregation") or "__none__",
                "metric_column": plan.get("metric_column") or "__none__",
                "dimension_column": plan.get("dimension_column") or "__none__",
                "plan": plan,
                "sql": sql,
                "params": params,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            intent_counts[plan["intent"]] += 1
            table_counts[table["name"]] += 1
            domain_counts[table["domain"]] = domain_counts.get(table["domain"], 0) + 1
            complex_counts["joined_queries"] += int(bool(plan.get("joins")))
            complex_counts["multi_filter_queries"] += int(len(plan.get("filters", [])) >= 2)
            complex_counts["time_filter_queries"] += int(bool(plan.get("time_field")))
            complex_counts["remote_dimension_queries"] += int(
                bool(plan.get("dimension_table"))
                and plan.get("dimension_table") != table["name"]
            )
        monthly_end = base_count + monthly_report_count
        for index in range(base_count, monthly_end):
            for _ in range(100):
                plan, question = _make_monthly_learning_report_sample(rng, catalog)
                if question not in seen_questions:
                    seen_questions.add(question)
                    break
            else:
                raise RuntimeError("无法继续生成不重复的部门逐月人均学习时长问句")
            sql, params = compiler.compile(plan)
            record = {
                "id": index,
                "question": question,
                "intent": "cross_tab",
                "domain": "training",
                "table": "Student_Course_Log",
                "aggregation": "avg",
                "metric_column": "__derived_session_duration__",
                "dimension_column": "Department",
                "plan": plan,
                "sql": sql,
                "params": params,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            intent_counts["cross_tab"] += 1
            table_counts["Student_Course_Log"] += 1
            domain_counts["training"] = domain_counts.get("training", 0) + 1
            complex_counts["joined_queries"] += 1
            complex_counts["time_filter_queries"] += 1
            complex_counts["remote_dimension_queries"] += 1
            complex_counts["cross_tab_queries"] += 1
        exam_score_end = monthly_end + exam_score_count
        for index in range(monthly_end, exam_score_end):
            for _ in range(100):
                plan, question = _make_exam_score_sample(rng, semantic_layer)
                if question not in seen_questions:
                    seen_questions.add(question)
                    break
            else:
                raise RuntimeError("无法继续生成不重复的多人课程成绩问句")
            sql, params = compiler.compile(plan)
            record = {
                "id": index,
                "question": question,
                "intent": "group_aggregate",
                "domain": "exam",
                "table": "clerk_kscj",
                "aggregation": plan["aggregation"],
                "metric_column": "Cj",
                "dimension_column": "ActualName",
                "plan": plan,
                "sql": sql,
                "params": params,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            intent_counts["group_aggregate"] += 1
            table_counts["clerk_kscj"] += 1
            domain_counts["exam"] = domain_counts.get("exam", 0) + 1
            complex_counts["joined_queries"] += 1
            complex_counts["multi_filter_queries"] += 1
            complex_counts["time_filter_queries"] += int(bool(plan.get("time_field")))
            complex_counts["remote_dimension_queries"] += 1
            complex_counts["compositional_exam_score_queries"] = (
                complex_counts.get("compositional_exam_score_queries", 0) + 1
            )
        for index in range(exam_score_end, count):
            for _ in range(100):
                plan, question = _make_exam_score_ranking_sample(rng, semantic_layer)
                if question not in seen_questions:
                    seen_questions.add(question)
                    break
            else:
                raise RuntimeError("无法继续生成不重复的学员成绩排名问句")
            sql, params = compiler.compile(plan)
            record = {
                "id": index,
                "question": question,
                "intent": "top_n",
                "domain": "exam",
                "table": "clerk_kscj",
                "aggregation": plan["aggregation"],
                "metric_column": "Cj",
                "dimension_column": "ActualName",
                "plan": plan,
                "sql": sql,
                "params": params,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            intent_counts["top_n"] += 1
            table_counts["clerk_kscj"] += 1
            domain_counts["exam"] = domain_counts.get("exam", 0) + 1
            complex_counts["joined_queries"] += 1
            complex_counts["multi_filter_queries"] += int(len(plan.get("filters", [])) >= 2)
            complex_counts["time_filter_queries"] += int(bool(plan.get("time_field")))
            complex_counts["remote_dimension_queries"] += 1
            complex_counts["exam_score_ranking_queries"] += 1
    return {
        "samples": count,
        "base_samples": base_count,
        "specialized_report_samples": special_total,
        "monthly_report_samples": monthly_report_count,
        "compositional_exam_score_samples": exam_score_count,
        "exam_score_ranking_samples": exam_score_ranking_count,
        "tables_covered": sum(value > 0 for value in table_counts.values()),
        "base_table_min_samples": base_count // len(tables),
        "base_table_max_samples": (base_count + len(tables) - 1) // len(tables),
        "table_min_samples": min(table_counts.values()),
        "table_max_samples": max(table_counts.values()),
        "intents": intent_counts,
        "domains": domain_counts,
        "complexity": complex_counts,
        "unique_questions": len(seen_questions),
    }


def _make_monthly_learning_report_sample(
    rng: random.Random,
    catalog: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    year = rng.randint(2022, 2030)
    year_phrase = rng.choice([f"{year}年度", f"{year}年", f"{year}全年"])
    department = rng.choice(["各部门", "不同部门", "所有部门", "部门", "部门之间"])
    month = rng.choice(["一至十二月份", "一到十二月", "1至12月份", "1到12月", "每个月", "逐月", "月度"])
    per_capita = rng.choice(["人均", "平均每人", "每人平均", "每位员工平均", "平均每位员工", "员工人均"])
    metric = rng.choice(["学习时长", "学习时间", "学习用时", "培训时长", "培训学时", "课程学习时间", "学习小时"])
    comparison = rng.choice(["横向对比", "趋势报表", "对比表", "比较", "交叉汇总", "汇总报表", "统计"])
    prefix = rng.choice(["", "请生成", "帮我查看", "我想看", "请统计", "给我", "输出", "查询"])
    templates = (
        "{prefix}{year}{department}{month}{per_capita}{metric}{comparison}",
        "{prefix}{year}{month}{department}{per_capita}{metric}{comparison}",
        "{prefix}{department}{year}{month}{per_capita}{metric}{comparison}",
        "{prefix}{year}按{department}{month}统计{per_capita}{metric}{comparison}",
        "{prefix}{year}{department}{per_capita}{metric}{month}{comparison}",
    )
    question = _clean(
        rng.choice(templates).format(
            prefix=prefix,
            year=year_phrase,
            department=department,
            month=month,
            per_capita=per_capita,
            metric=metric,
            comparison=comparison,
        )
    )
    plan = build_monthly_department_learning_plan(
        question, year, catalog, year_phrase
    )
    return plan, question


def _make_exam_score_sample(
    rng: random.Random,
    semantic_layer: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    names = ["张三", "李四", "王五", "赵敏", "陈晨", "刘洋", "孙强", "周静", "吴磊", "郑洁", "杨帆", "何平"]
    people = rng.sample(names, rng.choice([2, 2, 2, 3]))
    connector = rng.choice(["和", "与", "、", "及", "以及", "跟"])
    people_text = connector.join(people)
    marker = rng.choice(["各自", "分别", "每人", "各人"])
    courses = ["线性代数", "高等数学", "安全生产", "数据分析", "项目管理", "职业道德", "计算机基础", "应急管理", "财务基础", "质量管理"]
    course = rng.choice(courses)
    year = rng.randint(2022, 2030)
    year_text = rng.choice([f"{year}年", f"{year}年度", f"{year}全年"])
    aggregation = rng.choice(["max", "max", "min", "avg"])
    aggregation_text = rng.choice(
        {
            "max": ["最高分", "最高成绩", "最好成绩", "最高得分"],
            "min": ["最低分", "最低成绩", "最低得分"],
            "avg": ["平均分", "平均成绩", "平均得分"],
        }[aggregation]
    )
    prefix = rng.choice(["", "查询", "统计", "请查看", "帮我查", "列出", "我想知道"])
    templates = (
        "{prefix}{year}{people}{marker}在{course}中取得的{metric}",
        "{prefix}{year}{people}{marker}在{course}课程中的{metric}",
        "{prefix}{people}{marker}{year}在课程名称为{course}的考试中的{metric}",
        "{prefix}课程为{course}时{people}{marker}{year}的{metric}",
        "{prefix}{year}{course}这门课中{people}{marker}取得的{metric}",
    )
    question = _clean(
        rng.choice(templates).format(
            prefix=prefix,
            year=year_text,
            people=people_text,
            marker=marker,
            course=course,
            metric=aggregation_text,
        )
    )
    plan = build_exam_score_plan(
        question=question,
        people=people,
        course_name=course,
        aggregation=aggregation,
        year=year,
        semantic_layer=semantic_layer,
        time_expression=year_text,
    )
    return plan, question


def _make_exam_score_ranking_sample(
    rng: random.Random,
    semantic_layer: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    year = rng.randint(2020, 2032)
    year_text = rng.choice([f"{year}年", f"{year}年度", f"{year}全年"])
    aggregation = rng.choice(["avg", "avg", "avg", "max", "min"])
    metric = rng.choice(
        {
            "avg": ["平均成绩", "平均分", "平均得分", "成绩均值"],
            "max": ["最高分", "最高成绩", "最高得分"],
            "min": ["最低分", "最低成绩", "最低得分"],
        }[aggregation]
    )
    order = rng.choice(["desc", "desc", "asc"])
    if aggregation == "max":
        order = "desc"
    ranking_word = rng.choice(
        [
            f"{'最高的' if order == 'desc' else '最低的'}前{{limit}}名",
            f"排名{'前' if order == 'desc' else '倒数'}{{limit}}名",
            f"排行{'前' if order == 'desc' else '倒数'}{{limit}}名",
            f"{'最好' if order == 'desc' else '最差'}的{{limit}}个",
        ]
    )
    limit = rng.choice([3, 5, 10, 20, 50])
    ranking_word = ranking_word.format(limit=limit)
    student_word = rng.choice(["学生", "学员", "考生", "人员"])
    prefix = rng.choice(["", "查询", "统计", "请查看", "筛选", "教务报表", "考试后台查看"])
    scope = rng.choice(["specific", "specific", "all_courses", "all_exams"])
    courses = ["线性代数", "高等数学", "安全生产", "数据分析", "项目管理", "职业道德", "计算机基础", "应急管理", "财务基础", "质量管理"]
    departments = [None, None, "研发部", "培训部", "生产部", "人力资源部", "教务处", "考试中心"]
    department = rng.choice(departments) if scope != "specific" else None
    if scope == "specific":
        course = rng.choice(courses)
        scope_text = rng.choice([course, f"{course}课程", f"课程名称为{course}的考试"])
    elif scope == "all_courses":
        course = None
        scope_text = rng.choice(["所有课程", "全部课程", "各门课程"])
    else:
        course = None
        scope_text = rng.choice(["所有考试", "全部考试", "各类考试"])
    department_text = department or ""
    templates = (
        "{prefix}{year}{department}{scope}{metric}{ranking}{student}",
        "{prefix}{department}{year}{scope}{metric}{ranking}{student}",
        "{prefix}{year}{department}{student}{scope}{metric}{ranking}",
        "{prefix}{year}{department}{scope}{student}{metric}{ranking}",
    )
    question = _clean(
        rng.choice(templates).format(
            prefix=prefix,
            year=year_text,
            department=department_text,
            scope=scope_text,
            metric=metric,
            ranking=ranking_word,
            student=student_word,
        )
    )
    plan = build_exam_score_ranking_plan(
        question=question,
        aggregation=aggregation,
        limit=limit,
        order=order,
        year=year,
        course_name=course,
        course_scope=scope,
        department=department,
        semantic_layer=semantic_layer,
        time_expression=year_text,
    )
    return plan, question


def _make_sample(
    table: dict[str, Any],
    catalog: dict[str, Any],
    dictionary: dict[str, Any],
    rng: random.Random,
    reference: date,
    alias_counts: Counter[str],
    entity_routes: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    numeric = numeric_fields(table)
    dimensions = dimension_fields(table)
    dates = date_fields(table)
    supported = ["list", "count"]
    if numeric:
        supported.append("aggregate")
    if dimensions or any(route["table"] != table["name"] for route in entity_routes):
        supported.append("group_aggregate")
        supported.append("top_n")
    intent = rng.choices(supported, weights=[18, 22] + [20] * (len(supported) - 2), k=1)[0]
    table_word = _choose_alias(table["aliases"], table["label"], rng, alias_counts)
    prefix = rng.choice(["", "请", "帮我", "麻烦", "我想查看", "请问", "我需要", "给我"])
    metric = rng.choice(numeric) if numeric else None
    usable_dimensions = [
        field for field in dimensions if metric is None or field["name"] != metric["name"]
    ]
    dimension = rng.choice(usable_dimensions or dimensions) if dimensions else None
    dimension_table = table["name"] if dimension else None
    joins: list[dict[str, Any]] = []
    if (
        intent in {"group_aggregate", "top_n"}
        and entity_routes
        and (dimension is None or rng.random() < 0.24)
    ):
        remote = [route for route in entity_routes if route["table"] != table["name"]]
        if remote:
            chosen = rng.choice(remote)
            dimension = chosen["field"]
            dimension_table = chosen["table"]
            joins.extend(chosen["path"])
    aggregation = None
    if intent == "aggregate":
        aggregation = rng.choice(["sum", "avg", "max", "min"])
    elif intent == "group_aggregate":
        aggregation = rng.choice(["sum", "avg", "max", "min"]) if metric else "count"
    elif intent == "top_n":
        # A ranking question without an explicit operator is compiled using a
        # stable business default: SUM for numeric measures, COUNT otherwise.
        aggregation = "sum" if metric else "count"
    metric_word = _field_alias(metric, rng) if metric else "记录数量"
    dimension_word = _field_alias(dimension, rng) if dimension else ""
    agg_word = _aggregation_word(aggregation, rng)

    filters: list[dict[str, Any]] = []
    filter_parts: list[str] = []
    local_candidates = [
        field
        for field in dimensions
        if not (
            dimension
            and dimension_table == table["name"]
            and field["name"] == dimension["name"]
        )
    ]
    if local_candidates and rng.random() < 0.52:
        rng.shuffle(local_candidates)
        filter_count = 2 if len(local_candidates) >= 2 and rng.random() < 0.28 else 1
        for filter_field in local_candidates[:filter_count]:
            value = _sample_value(filter_field, table, rng)
            filters.append(
                {
                    "table": table["name"],
                    "field": filter_field["name"],
                    "operator": "=",
                    "value": value,
                }
            )
            filter_parts.append(f"{_field_alias(filter_field, rng)}为{value}")

    if entity_routes and rng.random() < 0.34:
        candidates = [
            route
            for route in entity_routes
            if not (
                dimension
                and dimension_table == route["table"]
                and dimension["name"] == route["field"]["name"]
            )
        ]
        if candidates:
            route = rng.choice(candidates)
            value = rng.choice(route["spec"].get("sample_values", ["示例值"]))
            filters.append(
                {
                    "table": route["table"],
                    "field": route["field"]["name"],
                    "operator": "=",
                    "value": value,
                    "entity_type": route["entity_type"],
                }
            )
            joins.extend(route["path"])
            filter_parts.append(_entity_filter_text(route["entity_type"], value, rng).rstrip("的"))

    filter_text = "且".join(filter_parts) + ("的" if filter_parts else "")

    date_start = date_end = time_field = None
    time_text = ""
    if dates and rng.random() < 0.48:
        time_text, time_kind = rng.choice(TIME_PHRASES[1:])
        date_start, date_end = resolve_generated_time(time_kind, reference)
        time_field = rng.choice(dates)["name"]

    plan: dict[str, Any] = {
        "intent": intent,
        "domain": table["domain"],
        "table": table["name"],
        "metric_column": metric["name"] if metric and intent in {"aggregate", "group_aggregate", "top_n"} else None,
        "metric_table": table["name"] if metric and intent in {"aggregate", "group_aggregate", "top_n"} else None,
        "dimension_column": dimension["name"] if dimension and intent in {"group_aggregate", "top_n"} else None,
        "dimension_table": dimension_table if dimension and intent in {"group_aggregate", "top_n"} else None,
        "aggregation": aggregation,
        "filters": filters,
        "joins": _deduplicate_joins(joins),
        "time_field": time_field,
        "date_start": date_start,
        "date_end": date_end,
        "limit": None,
        "order": "desc",
    }
    context = time_text + filter_text
    if intent == "list":
        templates = [
            "{p}查询{ctx}{table}记录",
            "{p}列出{ctx}{table}明细",
            "{p}显示{ctx}{table}数据",
            "{p}查看{ctx}{table}",
            "{p}{ctx}{table}有哪些记录",
            "{p}把{ctx}{table}明细列出来",
            "{p}给出{ctx}{table}清单",
        ]
    elif intent == "count":
        templates = [
            "{p}统计{ctx}{table}数量",
            "{p}{ctx}{table}有多少条",
            "{p}查询{ctx}{table}总数",
            "{p}计算{ctx}{table}记录数",
            "{p}{ctx}{table}一共有多少个",
            "{p}汇总{ctx}{table}的记录数量",
        ]
    elif intent == "aggregate":
        templates = [
            "{p}统计{ctx}{table}的{agg}{metric}",
            "{p}查询{ctx}{table}{metric}的{agg}",
            "{p}计算{ctx}{table}的{agg}{metric}",
            "{p}{ctx}{table}在{metric}上的{agg}是多少",
            "{p}给出{ctx}{table}{metric}的{agg}值",
        ]
    elif intent == "group_aggregate":
        templates = [
            "{p}按{dim}统计{ctx}{table}的{agg}{metric}",
            "{p}统计{ctx}{table}每个{dim}的{agg}{metric}",
            "{p}分别查看{ctx}{table}各{dim}的{agg}{metric}",
            "{p}{ctx}{table}按{dim}分别统计{agg}{metric}",
            "{p}给出{ctx}{table}以{dim}划分的{agg}{metric}",
        ]
    else:
        limit = rng.choice([3, 5, 10, 20])
        ascending = rng.random() < 0.2
        plan["limit"] = limit
        plan["order"] = "asc" if ascending else "desc"
        direction = rng.choice(["最低", "最少", "最小"]) if ascending else rng.choice(["最高", "最多", "最大"])
        templates = [
            "{p}查询{ctx}{table}{metric}{direction}的前{n}个{dim}",
            "{p}列出{ctx}{table}按{metric}排名前{n}的{dim}",
            "{p}查看{ctx}{table}各{dim}的{metric}Top{n}",
            "{p}{ctx}{table}中{dim}按{metric}排序取前{n}",
            "{p}给出{ctx}{table}{metric}{direction}的{n}个{dim}",
        ]
    question = rng.choice(templates).format(
        p=prefix,
        ctx=context,
        table=table_word,
        agg=agg_word,
        metric=metric_word,
        dim=dimension_word,
        n=plan.get("limit") or "",
        direction=locals().get("direction", ""),
    )
    return plan, _clean(question)


def _build_entity_routes(
    table: dict[str, Any], catalog: dict[str, Any], dictionary: dict[str, Any]
) -> list[dict[str, Any]]:
    tables = {item["name"]: item for item in catalog["tables"]}
    routes: list[dict[str, Any]] = []
    for entity_type, spec in dictionary.get("entities", {}).items():
        target = spec["table"]
        if target not in tables or spec["field"] not in field_map(tables[target]):
            continue
        path = find_join_path(catalog, table["name"], target, max_hops=3)
        if path is None or not is_safe_entity_path(table["name"], target, path):
            continue
        routes.append(
            {
                "entity_type": entity_type,
                "table": target,
                "field": field_map(tables[target])[spec["field"]],
                "spec": spec,
                "path": path,
            }
        )
    return routes


def _entity_filter_text(entity_type: str, value: str, rng: random.Random) -> str:
    if entity_type == "person_name":
        return rng.choice([f"{value}的", f"姓名为{value}的", f"学员姓名为{value}的"])
    labels = {
        "user_name": "用户名",
        "course_name": "课程名称",
        "study_class_name": "学习班名称",
        "department_name": "部门",
        "offtrain_name": "面授课程",
        "skill_name": "能力名称",
    }
    return f"{labels.get(entity_type, entity_type)}为{value}的"


def _deduplicate_joins(joins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[Any, dict[str, Any]] = {}
    for rule in joins:
        unique.setdefault(join_rule_key(rule), rule)
    return list(unique.values())


def _choose_alias(
    aliases: list[str],
    fallback: str,
    rng: random.Random,
    alias_counts: Counter[str],
) -> str:
    # Ambiguous fragments such as “考评活动” occur on several related tables.
    # Training on them as if they identified one exact table creates contradictory
    # labels, so synthetic questions use only distinctive aliases.
    chinese = [
        alias
        for alias in aliases
        if re.search(r"[\u4e00-\u9fff]", alias)
        and len(alias) >= 2
        and alias_counts[_normalize_alias(alias)] == 1
    ]
    return rng.choice(chinese or [fallback] or aliases)


def _field_alias(field: dict[str, Any] | None, rng: random.Random) -> str:
    if not field:
        return "数量"
    chinese = [
        alias
        for alias in field.get("aliases", [])
        if re.search(r"[\u4e00-\u9fff]", alias)
        and len(alias) <= 12
        and not re.search(r"[=<>|]", alias)
        and not re.match(r"^\d", alias)
    ]
    return rng.choice(chinese or field.get("aliases", []) or [field["name"]])


def _normalize_alias(text: str) -> str:
    return re.sub(r"[\s，。！？、,!?()（）表]", "", text.lower())


def _aggregation_word(name: str | None, rng: random.Random) -> str:
    words = {
        "sum": ["合计", "总和", "累计"],
        "avg": ["平均", "均值"],
        "max": ["最大", "最高"],
        "min": ["最小", "最低"],
        "count": ["数量", "总数"],
        None: [""],
    }
    return rng.choice(words[name])


def _sample_value(field: dict[str, Any], table: dict[str, Any], rng: random.Random) -> Any:
    name = field["name"].lower()
    if "status" in name:
        return rng.choice([0, 1])
    if "sex" in name:
        return rng.choice(["男", "女"])
    if "type" in name or "level" in name:
        return rng.choice([0, 1, 2])
    if is_numeric(field):
        return rng.choice([1, 10, 60, 100])
    if "name" in name or "title" in name:
        return rng.choice(["示例名称", "年度培训", "在线课程"])
    return rng.choice(["启用", "示例值", f"{table['label']}A"])


def resolve_generated_time(kind: str | None, reference: date) -> tuple[str | None, str | None]:
    if not kind:
        return None, None
    if kind == "today":
        return reference.isoformat(), (reference + timedelta(days=1)).isoformat()
    if kind == "yesterday":
        return (reference - timedelta(days=1)).isoformat(), reference.isoformat()
    if kind == "this_month":
        start = reference.replace(day=1)
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start.isoformat(), end.isoformat()
    if kind == "last_month":
        end = reference.replace(day=1)
        start = (end - timedelta(days=1)).replace(day=1)
        return start.isoformat(), end.isoformat()
    if kind == "this_year":
        return date(reference.year, 1, 1).isoformat(), date(reference.year + 1, 1, 1).isoformat()
    if kind == "last_year":
        return date(reference.year - 1, 1, 1).isoformat(), date(reference.year, 1, 1).isoformat()
    days = int(kind.split("_")[1])
    return (reference - timedelta(days=days - 1)).isoformat(), (reference + timedelta(days=1)).isoformat()


def _clean(text: str) -> str:
    text = text.replace("的的", "的")
    return re.sub(r"\s+", "", text).strip()
