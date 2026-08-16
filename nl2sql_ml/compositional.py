from __future__ import annotations

import re
from datetime import date
from typing import Any, Callable


EXAM_SCORE_AGGREGATE_QUERY = "student_exam_score_aggregate"
EXAM_SCORE_RANKING_QUERY = "student_exam_score_ranking"


def detect_compositional_query(
    question: str,
    normalized_text: str,
    semantic_layer: dict[str, Any],
    today: date,
    surname_chars: str,
    valid_person_name: Callable[[str], bool],
) -> dict[str, Any] | None:
    aggregation = _score_aggregation(normalized_text)
    ranking_limit = _score_ranking_limit(normalized_text)
    if aggregation is not None and ranking_limit is not None and any(
        word in normalized_text for word in ("学生", "学员", "考生", "人员")
    ):
        unsupported_attribute = _unsupported_student_attribute(normalized_text)
        if unsupported_attribute:
            attribute, value = unsupported_attribute
            raise ValueError(
                f"设计书中的Student_Info学员表没有{attribute}字段，无法按“{value}”筛选学生；"
                f"请确认{attribute}存储字段或改用部门等已定义维度"
            )
        all_courses = any(
            word in normalized_text for word in ("所有课程", "全部课程", "各门课程", "全课程")
        )
        all_exams = any(
            word in normalized_text for word in ("所有考试", "全部考试", "各类考试", "全部测验")
        )
        course = (
            None
            if all_courses or all_exams
            else (_course_name(normalized_text) or _ranking_course_name(normalized_text))
        )
        course_scope = (
            "specific"
            if course
            else "all_courses"
            if all_courses
            else "all_exams"
        )
        year, time_expression = _calendar_year(normalized_text, today)
        return build_exam_score_ranking_plan(
            question=question,
            aggregation=aggregation,
            limit=ranking_limit,
            order=_score_ranking_order(normalized_text),
            year=year,
            course_name=course,
            course_scope=course_scope,
            department=_student_department(normalized_text),
            semantic_layer=semantic_layer,
            time_expression=time_expression,
        )
    people = _person_list(normalized_text, surname_chars, valid_person_name)
    if not people:
        single_person = _single_person(
            normalized_text, surname_chars, valid_person_name
        )
        people = [single_person] if single_person else []
    if aggregation is None or not people:
        return None
    if len(people) > 1 and not any(
        word in normalized_text for word in ("各自", "分别", "每人", "各人")
    ):
        raise ValueError("识别到多名学员和成绩指标，但没有明确是分别统计还是合并统计")
    course = _course_name(normalized_text)
    year, time_expression = _calendar_year(normalized_text, today)
    return build_exam_score_plan(
        question=question,
        people=people,
        course_name=course,
        aggregation=aggregation,
        year=year,
        semantic_layer=semantic_layer,
        time_expression=time_expression,
    )


def build_exam_score_ranking_plan(
    question: str,
    aggregation: str,
    limit: int,
    order: str,
    year: int | None,
    course_name: str | None,
    course_scope: str,
    department: str | None,
    semantic_layer: dict[str, Any],
    time_expression: str | None = None,
) -> dict[str, Any]:
    fact = semantic_layer.get("facts", {}).get("exam_score")
    if not fact:
        raise ValueError("业务语义层没有定义exam_score事实")
    measure = fact.get("measures", {}).get("score", {})
    if aggregation not in measure.get("allowed_aggregations", []):
        raise ValueError(f"考试成绩事实不允许聚合方式: {aggregation}")
    if not 1 <= limit <= 1000:
        raise ValueError("成绩排名数量必须为1至1000")
    if order not in {"asc", "desc"}:
        raise ValueError("成绩排名方向无效")
    if course_scope not in {"specific", "all_courses", "all_exams"}:
        raise ValueError("成绩排名的课程范围无效")
    if course_scope == "specific" and not course_name:
        raise ValueError("指定课程排名缺少课程名称")
    if year is not None and not 2000 <= year <= 2100:
        raise ValueError(f"查询年度超出允许范围: {year}")

    relationships = fact.get("relationships", [])
    selected_relationships = relationships if course_scope != "all_exams" else relationships[:2]
    filters: list[dict[str, Any]] = []
    if department:
        filters.append(
            {
                "table": "Student_Info",
                "field": "Department",
                "operator": "=",
                "value": department,
                "entity_type": "department",
            }
        )
    if course_name:
        filters.append(
            {
                "table": "Course_Info",
                "field": "Name",
                "operator": "=",
                "value": course_name,
                "entity_type": "course_name",
            }
        )
    filters.extend(fact.get("row_filters", []))
    date_start = date(year, 1, 1).isoformat() if year is not None else None
    date_end = date(year + 1, 1, 1).isoformat() if year is not None else None
    aggregation_label = {"max": "最高成绩", "min": "最低成绩", "avg": "平均成绩"}[aggregation]
    assumptions = list(fact.get("assumptions", [])) if course_scope != "all_exams" else []
    assumptions.append("姓名相同的不同学员按Student_Info.Id分别参与排名")
    return {
        "question": question,
        "report_type": EXAM_SCORE_RANKING_QUERY,
        "intent": "top_n",
        "domain": "exam",
        "table": "clerk_kscj",
        "fact": "exam_score",
        "metric_column": measure.get("field", "Cj"),
        "metric_table": measure.get("table", "clerk_kscj"),
        "dimension_column": "ActualName",
        "dimension_table": "Student_Info",
        "aggregation": aggregation,
        "filters": filters,
        "joins": selected_relationships,
        "entities": [
            *(
                [{"type": "department", "value": department, "table": "Student_Info", "field": "Department"}]
                if department
                else []
            ),
            *(
                [{"type": "course_name", "value": course_name, "table": "Course_Info", "field": "Name"}]
                if course_name
                else []
            ),
        ],
        "unresolved_entities": [],
        "time_field": fact.get("time", {}).get("field", "clerk_ks_btime"),
        "date_start": date_start,
        "date_end": date_end,
        "time_expression": time_expression,
        "limit": limit,
        "order": order,
        "semantic_ast": {
            "type": "ranking_query",
            "fact": "exam_score",
            "measure": {"name": "score", "aggregation": aggregation},
            "dimensions": ["student"],
            "filters": {
                "department": department,
                "course_name": course_name,
                "course_scope": course_scope,
                "calendar_year": year,
            },
            "ranking": {"limit": limit, "order": order},
            "output_label": aggregation_label,
        },
        "confidence": {"intent": 1.0, "domain": 1.0, "table": 1.0, "aggregation": 1.0},
        "sources": {"table": "semantic_layer", "metric": "semantic_layer"},
        "warnings": assumptions,
    }


def build_exam_score_plan(
    question: str,
    people: list[str],
    course_name: str | None,
    aggregation: str,
    year: int | None,
    semantic_layer: dict[str, Any],
    time_expression: str | None = None,
) -> dict[str, Any]:
    fact = semantic_layer.get("facts", {}).get("exam_score")
    if not fact:
        raise ValueError("业务语义层没有定义exam_score事实")
    measure = fact.get("measures", {}).get("score", {})
    if aggregation not in measure.get("allowed_aggregations", []):
        raise ValueError(f"考试成绩事实不允许聚合方式: {aggregation}")
    clean_people = list(dict.fromkeys(name.strip() for name in people if name.strip()))
    if not clean_people or len(clean_people) > 20:
        raise ValueError("学员姓名数量必须为1至20个")
    if year is not None and not 2000 <= year <= 2100:
        raise ValueError(f"查询年度超出允许范围: {year}")

    relationships = fact.get("relationships", [])
    selected_relationships = relationships[:2]
    if course_name:
        selected_relationships = relationships
    filters: list[dict[str, Any]] = [
        {
            "table": "Student_Info",
            "field": "ActualName",
            "operator": "IN",
            "value": clean_people,
            "entity_type": "person_name",
        }
    ]
    if course_name:
        filters.append(
            {
                "table": "Course_Info",
                "field": "Name",
                "operator": "=",
                "value": course_name,
                "entity_type": "course_name",
            }
        )
    filters.extend(fact.get("row_filters", []))
    date_start = date(year, 1, 1).isoformat() if year is not None else None
    date_end = date(year + 1, 1, 1).isoformat() if year is not None else None
    aggregation_label = {"max": "最高", "min": "最低", "avg": "平均"}[aggregation]
    assumptions = list(fact.get("assumptions", [])) if course_name else []
    assumptions.append("姓名相同的不同学员按Student_Info.Id分别输出")
    return {
        "question": question,
        "report_type": EXAM_SCORE_AGGREGATE_QUERY,
        "intent": "group_aggregate",
        "domain": "exam",
        "table": "clerk_kscj",
        "fact": "exam_score",
        "metric_column": measure.get("field", "Cj"),
        "metric_table": measure.get("table", "clerk_kscj"),
        "dimension_column": "ActualName",
        "dimension_table": "Student_Info",
        "aggregation": aggregation,
        "filters": filters,
        "joins": selected_relationships,
        "entities": [
            *(
                {
                    "type": "person_name",
                    "value": name,
                    "table": "Student_Info",
                    "field": "ActualName",
                }
                for name in clean_people
            ),
            *(
                [
                    {
                        "type": "course_name",
                        "value": course_name,
                        "table": "Course_Info",
                        "field": "Name",
                    }
                ]
                if course_name
                else []
            ),
        ],
        "unresolved_entities": [],
        "time_field": fact.get("time", {}).get("field", "clerk_ks_btime"),
        "date_start": date_start,
        "date_end": date_end,
        "time_expression": time_expression,
        "limit": None,
        "order": "asc",
        "semantic_ast": {
            "type": "aggregate_query",
            "fact": "exam_score",
            "measure": {"name": "score", "aggregation": aggregation},
            "dimensions": ["student"],
            "filters": {
                "student_name": {"operator": "in", "values": clean_people},
                "course_name": course_name,
                "calendar_year": year,
            },
            "output_label": f"{aggregation_label}分",
        },
        "confidence": {
            "intent": 1.0,
            "domain": 1.0,
            "table": 1.0,
            "aggregation": 1.0,
        },
        "sources": {"table": "semantic_layer", "metric": "semantic_layer"},
        "warnings": assumptions,
    }


def _score_aggregation(text: str) -> str | None:
    if any(word in text for word in ("最高分", "最高成绩", "最好成绩", "最大分数", "最高得分")):
        return "max"
    if any(word in text for word in ("最低分", "最低成绩", "最差成绩", "最小分数", "最低得分")):
        return "min"
    if any(word in text for word in ("平均分", "平均成绩", "平均得分", "成绩均值")):
        return "avg"
    return None


def _score_ranking_limit(text: str) -> int | None:
    if not any(word in text.lower() for word in ("前", "top", "排名", "排行", "名次", "榜", "最高", "最低", "最好", "最差", "倒数")):
        return None
    patterns = (
        r"前(\d+)(?:名|个)?",
        r"top(\d+)",
        r"(?:排名|排行|名次)?倒数(\d+)(?:名|个)?",
        r"(?:最高|最低|最好|最差)的?(\d+)(?:名|个)",
        r"(\d+)(?:名|个)(?:学生|学员|考生|人员)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return max(1, min(int(match.group(1)), 1000))
    chinese = {"三": 3, "五": 5, "十": 10, "二十": 20, "五十": 50, "一百": 100}
    for word, value in chinese.items():
        if re.search(rf"(?:前|最高的?|最低的?){word}(?:名|个)?", text):
            return value
    return 10 if any(word in text for word in ("排名", "排行", "榜")) else None


def _score_ranking_order(text: str) -> str:
    if any(word in text for word in ("排名倒数", "排行倒数", "名次倒数", "倒数", "最低的前", "最差的", "末位")):
        return "asc"
    if any(word in text for word in ("排名前", "排行前", "最高的前", "最好的")):
        return "desc"
    return "asc" if re.search(r"(?:平均成绩|平均分|平均得分|成绩均值)最低", text) else "desc"


def _unsupported_student_attribute(text: str) -> tuple[str, str] | None:
    cleaned = re.sub(r"20\d{2}(?:年度|全年|年)", "", text)
    cleaned = re.sub(r"^(?:查询|统计|请查看|帮我查|列出|筛选|请|帮我|麻烦)+", "", cleaned)
    patterns = (
        ("专业", r"(?P<value>[\u4e00-\u9fffA-Za-z0-9]{1,20}专业)(?=所有|全部|各|的|学生|学员|考生|人员)"),
        ("年级", r"(?P<value>[一二三四五六七八九十0-9]{1,4}年级)(?=所有|全部|各|的|学生|学员|考生|人员)"),
        ("学院", r"(?P<value>[\u4e00-\u9fffA-Za-z0-9]{1,20}学院)(?=所有|全部|各|的|学生|学员|考生|人员)"),
        ("班级", r"(?P<value>[一二三四五六七八九十0-9A-Za-z]{1,10}班)(?=所有|全部|各|的|学生|学员|考生|人员)"),
    )
    for attribute, pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            return attribute, match.group("value")
    return None


def _student_department(text: str) -> str | None:
    explicit = re.search(
        r"部门(?:为|是|等于|=)(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,30}?)(?=的|所有|全部|学生|学员|考生|平均|最高|最低|前|$)",
        text,
    )
    if explicit:
        return explicit.group("value")
    match = re.search(
        r"(?:考试后台查看|教务报表|请查看|筛选|查询|统计|查看|20\d{2}(?:年度|全年|年)|^)"
        r"(?P<value>[\u4e00-\u9fff]{1,10}(?:部|处|中心|科|室))"
        r"(?=20\d{2}(?:年度|全年|年)|所有|全部|各门|各类|学生|学员|考生|人员|的)",
        text,
    )
    return match.group("value") if match else None


def _person_list(
    text: str,
    surname_chars: str,
    valid_person_name: Callable[[str], bool],
) -> list[str]:
    surname_class = re.escape(surname_chars)
    name = rf"[{surname_class}][\u4e00-\u9fff]{{1,3}}"
    connector = r"(?:以及|和|与|、|及|跟)"
    marker = re.search(r"各自|分别|每人|各人", text)
    if marker:
        prefix = text[: marker.start()]
        prefix = re.sub(r"20\d{2}(?:年度|全年|年)", "", prefix)
        prefix = re.sub(r"今年|去年", "", prefix)
        prefix = re.sub(r"^(?:查询|统计|请查看|帮我查|列出|我想知道|请|帮我|麻烦)+", "", prefix)
        prefix = re.split(r"(?:时|中|里|的)", prefix)[-1]
        values = [value for value in re.split(connector, prefix) if value]
        if len(values) >= 2 and all(valid_person_name(value) for value in values):
            return values
    pattern = rf"(?P<names>{name}(?:{connector}{name})+?)(?=各自|分别|每人|各人|在|于|的|$)"
    match = re.search(pattern, text)
    if not match:
        return []
    values = [
        re.sub(r"(?:各自|分别|每人|各人)$", "", value)
        for value in re.split(connector, match.group("names"))
        if value
    ]
    return values if all(valid_person_name(value) for value in values) else []


def _single_person(
    text: str,
    surname_chars: str,
    valid_person_name: Callable[[str], bool],
) -> str | None:
    surname_class = re.escape(surname_chars)
    patterns = (
        rf"^(?:20\d{{2}}(?:年度|全年|年))?(?P<value>[{surname_class}][\u4e00-\u9fff]{{1,3}}?)(?=20\d{{2}}(?:年度|全年|年)|在|的)",
        rf"(?:查询|查看|请查看|帮我查|列出|统计|请|帮我|麻烦)(?P<value>[{surname_class}][\u4e00-\u9fff]{{1,3}}?)(?=20\d{{2}}(?:年度|全年|年)|在|的)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match and valid_person_name(match.group("value")):
            return match.group("value")
    return None


def _course_name(text: str) -> str | None:
    patterns = (
        r"(?:课程名称|课程名|课程)(?:为|是|等于|=)(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,30}?)(?=的|中|里|时|各自|分别|最高|最低|平均|$)",
        r"在(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,30}?)(?:课程|这门课)?(?:中|里)(?=取得|获得|考得|拿到|考出|的|最高|最低|平均)",
        r"在(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,30}?)(?=取得|获得|考得|拿到|考出)",
        r"的(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,30}?)(?=平均成绩|平均分|平均得分|成绩均值|最高成绩|最高分|最高得分|最低成绩|最低分|最低得分)",
        r"20\d{2}(?:年度|全年|年)(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,30}?)(?:这门课|课程)(?:中|里)",
        r"(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,30}?)(?:课程|这门课)(?:中|里|的)(?=最高|最低|平均|成绩|分数)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group("value").strip("的")
            if value not in {"考试", "所有", "全部", "各自", "分别"}:
                return value
    return None


def _ranking_course_name(text: str) -> str | None:
    cleaned = re.sub(r"20\d{2}(?:年度|全年|年)", "", text)
    cleaned = re.sub(
        r"^(?:考试后台查看|教务报表|查询|统计|请查看|帮我查|列出|筛选|请|帮我|麻烦)+",
        "",
        cleaned,
    )
    match = re.search(
        r"(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,30}?)(?:课程)?"
        r"(?=平均成绩|平均分|平均得分|成绩均值|最高成绩|最高分|最高得分|最低成绩|最低分|最低得分)",
        cleaned,
    )
    if not match:
        return None
    value = match.group("value")
    value = re.sub(r"^(?:学生|学员|考生|人员)", "", value)
    value = re.sub(r"(?:学生|学员|考生|人员)$", "", value)
    value = re.sub(r"课程$", "", value)
    if value in {"所有", "全部", "各门", "全"} or value.endswith(("部", "专业")):
        return None
    return value


def _calendar_year(text: str, today: date) -> tuple[int | None, str | None]:
    match = re.search(r"(20\d{2})(?:年度|全年|年)", text)
    if match:
        return int(match.group(1)), match.group(0)
    if "今年" in text:
        return today.year, "今年"
    if "去年" in text:
        return today.year - 1, "去年"
    return None, None
