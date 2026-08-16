from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


DOMAIN_PATTERNS = [
    ("account", "帐户系列", ("帐户", "机构", "学员", "部门", "岗位")),
    ("question_bank", "题库系列", ("题库", "题目", "题型")),
    ("exam", "考试系列", ("考试", "试卷", "答卷", "成绩", "测评")),
    ("training", "培训系列", ("培训", "课程", "课件", "学习班", "知识库")),
    ("forum", "论坛系列", ("论坛", "主题", "回帖")),
    ("configuration", "参数配置", ("参数", "配置")),
    ("notification", "消息通知", ("消息", "邮件", "通知")),
    ("system", "系统数据", ("系统", "权限", "角色", "菜单", "证书", "积分", "群组", "标签")),
    ("news", "资讯中心", ("资讯", "新闻", "栏目")),
    ("evaluation", "评分活动", ("评分", "考评", "评价活动")),
    ("game", "闯关游戏", ("闯关", "游戏", "关卡")),
    ("skill_matrix", "员工培训技能矩阵", ("能力", "技能", "矩阵")),
]

HEADER_ALIASES = {
    "field": ("字段名", "字段名称", "字段"),
    "type": ("类型",),
    "nullable": ("可空",),
    "default": ("默认值", "默认", "缺省"),
    "key": ("键",),
    "description": ("说明", "含义", "备注"),
}

GENERIC_FIELD_ALIASES = {
    "id": ["编号", "主键", "ID"],
    "name": ["名称"],
    "title": ["标题", "主题"],
    "userid": ["机构", "企业用户", "机构编号"],
    "studentid": ["学员", "人员", "员工", "学员编号"],
    "courseid": ["课程", "课程编号"],
    "coursewareid": ["课件", "课件编号"],
    "departmentid": ["部门", "部门编号"],
    "dutyid": ["岗位", "岗位编号"],
    "status": ["状态"],
    "type": ["类型"],
    "serialno": ["序号", "排序号"],
    "createtime": ["创建时间"],
    "createdtime": ["创建时间"],
    "begintime": ["开始时间"],
    "endtime": ["结束时间"],
    "finishtime": ["完成时间"],
    "logintime": ["登录时间"],
    "score": ["分数", "得分"],
    "total": ["总数", "合计"],
}

# The source heading for tm_tx contains only its physical name plus “表”, so
# these business terms cannot be recovered from the heading mechanically.
CURATED_TABLE_ALIASES = {
    "tm_tx": ["题型", "题型表"],
    "tk_tkj": ["章题库", "章题库集"],
    "tk_lx": ["题库", "题库表", "节题库", "节题库表"],
}

# The design-book heading names tk_lx as “题库集表”, while its field comments
# consistently define it as 节(题库).  Preserve the original label in the
# catalog, but remove the contradictory phrase from the query dictionary.
TABLE_ALIAS_EXCLUSIONS = {
    "tk_lx": {"题库集", "题库集表"},
}

ENTITY_DEFINITIONS = {
    "person_name": {
        "table": "Student_Info",
        "field": "ActualName",
        "aliases": ["姓名", "真实姓名", "学员姓名", "员工姓名", "人员姓名"],
        "sample_values": ["张三", "李四", "王五", "赵敏", "陈晨", "刘洋", "周宁", "吴桐"],
    },
    "user_name": {
        "table": "Student_Info",
        "field": "Name",
        "aliases": ["用户名", "登录名", "学员账号"],
        "sample_values": ["zhangsan", "lisi", "wangwu", "user001"],
    },
    "course_name": {
        "table": "Course_Info",
        "field": "Name",
        "aliases": ["课程名称", "课程"],
        "sample_values": ["年度培训", "安全生产", "新员工入职", "管理能力提升"],
    },
    "study_class_name": {
        "table": "Study_Class_Info",
        "field": "Name",
        "aliases": ["学习班名称", "学习班", "培训班"],
        "sample_values": ["2026新员工班", "安全生产班", "管理提升班"],
    },
    "department_name": {
        "table": "Student_Info",
        "field": "Department",
        "aliases": ["部门", "所属部门"],
        "sample_values": ["研发部", "培训部", "人力资源部", "生产部"],
    },
    "offtrain_name": {
        "table": "OffTrain_Info",
        "field": "Name",
        "aliases": ["面授课程", "线下培训", "线下课程"],
        "sample_values": ["现场安全培训", "管理人员面授班", "应急演练"],
    },
    "skill_name": {
        "table": "Skill_Info",
        "field": "Name",
        "aliases": ["能力名称", "技能名称", "能力", "技能"],
        "sample_values": ["沟通能力", "项目管理", "安全操作", "数据分析"],
    },
}


def clean_text(value: str) -> str:
    value = value.replace("\xa0", " ").replace("\u3000", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n/")


def iter_blocks(document: Document) -> Iterable[Paragraph | Table]:
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def detect_domain(text: str, current: tuple[str, str] | None) -> tuple[str, str] | None:
    compact = re.sub(r"[一二三四五六七八九十十二、：: \t]", "", text)
    for key, label, _ in DOMAIN_PATTERNS:
        if label in text or compact == label:
            return key, label
    return current


def english_identifiers(text: str) -> list[str]:
    return re.findall(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_]*)(?![A-Za-z0-9_])", text)


def choose_table_title(paragraphs: list[str]) -> tuple[str, str]:
    ignored = {"PK", "FK", "ID", "LGS", "SCORM"}
    for text in reversed(paragraphs):
        candidates = [item for item in english_identifiers(text) if item.upper() not in ignored]
        if not candidates:
            continue
        preferred = [item for item in candidates if "_" in item]
        if not preferred:
            preferred = [item for item in candidates if any(char.isupper() for char in item[1:])]
        name = (preferred or candidates)[0]
        if len(name) >= 2:
            return name, text
    raise ValueError(f"无法从标题中识别表名: {paragraphs[-5:]}")


def normalized_header(value: str) -> str | None:
    compact = clean_text(value).replace(" ", "")
    for standard, aliases in HEADER_ALIASES.items():
        if compact in aliases:
            return standard
    return None


def extract_fields(table: Table) -> tuple[list[dict[str, str]], list[list[str]], bool]:
    raw_rows = [[clean_text(cell.text) for cell in row.cells] for row in table.rows]
    if not raw_rows:
        return [], [], False
    parse_rows = [_collapse_adjacent(row) for row in raw_rows]
    header = [normalized_header(value) for value in parse_rows[0]]
    has_header = "field" in header
    no_type_layout = not has_header and not any(
        SQL_TYPE_PATTERN.match(value)
        for row in parse_rows
        for value in row[1:]
        if value
    )
    fields: list[dict[str, str]] = []
    data_rows = parse_rows[1:] if has_header else parse_rows
    for row in data_rows:
        field = _parse_field_row(row, no_type_layout=no_type_layout)
        if field:
            fields.append(field)
    return _deduplicate_fields(fields), raw_rows, has_header


def _collapse_adjacent(row: list[str]) -> list[str]:
    collapsed: list[str] = []
    for value in row:
        if collapsed and value == collapsed[-1]:
            continue
        collapsed.append(value)
    return collapsed


SQL_TYPE_PATTERN = re.compile(
    r"^(?:n?varchar|varhcar|n?char|text|ntext|bigint|smallint|tinyint|int|integer|float|double|decimal|numeric|money|real|bit|bool|datetime|datatime|dateime|smalldatetime|date|time|image|binary|varbinary|uniqueidentifier)(?:\s*\(|\b|/)",
    re.I,
)


def _parse_field_row(row: list[str], no_type_layout: bool = False) -> dict[str, str] | None:
    values = [clean_text(value) for value in row]
    nonempty = [(index, value) for index, value in enumerate(values) if value]
    if not nonempty:
        return None
    field_name = nonempty[0][1]
    if normalized_header(field_name):
        return None
    # Some source tables contain an in-grid change-note row such as
    # "304 新增字段".  It is documentation, not a SQL identifier.
    if not re.search(r"[A-Za-z]", field_name):
        return None
    if no_type_layout:
        description = " ".join(value for _, value in nonempty[1:])
        keys = []
        if re.search(r"\bPK\b|主键", description, re.I):
            keys.append("PK")
        if re.search(r"\bFK\b|外键", description, re.I):
            keys.append("FK")
        return {
            "name": field_name,
            "type": "UNKNOWN",
            "nullable": "",
            "default": "",
            "key": ",".join(keys),
            "description": description,
        }
    type_index = next((index for index, value in nonempty[1:] if SQL_TYPE_PATTERN.match(value)), None)
    type_value = values[type_index] if type_index is not None else "UNKNOWN"
    nullable_tokens = []
    key_tokens = []
    for index, value in nonempty[1:]:
        compact = value.replace(" ", "").lower()
        if compact in {"null", "notnull", "allownull", "notnullable"}:
            nullable_tokens.append(value)
        if re.search(r"\bPK\b|\bFK\b|主键|外键", value, re.I):
            if re.search(r"\bPK\b|主键", value, re.I):
                key_tokens.append("PK")
            if re.search(r"\bFK\b|外键", value, re.I):
                key_tokens.append("FK")
    description = nonempty[-1][1] if len(nonempty) > 1 else ""
    excluded = {field_name, type_value, description, *nullable_tokens}
    default_candidates = []
    for _, value in nonempty[1:-1]:
        if value in excluded or re.search(r"\bPK\b|\bFK\b|主键|外键", value, re.I):
            continue
        if value not in default_candidates:
            default_candidates.append(value)
    return {
        "name": field_name,
        "type": type_value,
        "nullable": " / ".join(dict.fromkeys(nullable_tokens)),
        "default": " / ".join(default_candidates),
        "key": ",".join(dict.fromkeys(key_tokens)),
        "description": description,
    }


def _deduplicate_fields(fields: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for field in fields:
        name = clean_text(field["name"]).replace("\n", "")
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", name):
            match = re.search(r"[A-Za-z][A-Za-z0-9_]*", name)
            if match:
                name = match.group(0)
        key = name.lower()
        if not name or key in seen:
            continue
        field["name"] = name
        field["type"] = normalize_type(field["type"])
        seen.add(key)
        result.append(field)
    return result


def normalize_type(value: str) -> str:
    value = clean_text(value).replace("（", "(").replace("）", ")")
    value = re.sub(r"\s+", "", value)
    corrections = {"varhcar": "varchar", "dateime": "datetime", "datatime": "datetime"}
    lowered = value.lower()
    for wrong, correct in corrections.items():
        lowered = lowered.replace(wrong, correct)
    if not lowered or lowered in {"unknown", "null", "notnull", "pk", "fk"}:
        return "UNKNOWN"
    return lowered


def chinese_title(title: str, table_name: str) -> str:
    text = re.sub(re.escape(table_name), "", title, flags=re.I)
    text = re.sub(r"[：:（）()\-]", " ", text)
    text = re.sub(r"\b(?:表|info)\b", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[一二三四五六七八九十十二、. ]+", "", text)
    return text or table_name


def aliases_for_table(table: dict[str, Any]) -> list[str]:
    label = table["label"]
    aliases = {table["name"], label, label.replace("表", "")}
    for segment in re.split(r"[\s/、]+", label):
        segment = segment.strip().replace("表", "")
        if len(segment) >= 2:
            aliases.add(segment)
    for token in re.split(r"[：:（）() /]+", table["title"]):
        token = clean_text(token)
        if token and token != table["name"] and len(token) <= 30:
            aliases.add(token.replace("表", ""))
    aliases.update(CURATED_TABLE_ALIASES.get(table["name"], []))
    aliases.difference_update(TABLE_ALIAS_EXCLUSIONS.get(table["name"], set()))
    return sorted((item for item in aliases if item), key=lambda item: (-len(item), item))


def aliases_for_field(field: dict[str, str]) -> list[str]:
    aliases = {field["name"]}
    description = field.get("description", "")
    first = re.split(r"[，。,；;（(：:/]|\\n", description)[0].strip()
    if first and len(first) <= 24 and not first.upper().startswith(("FK", "PK")):
        aliases.add(re.sub(r"^(?:FK|PK)\s*", "", first, flags=re.I))
    key = field["name"].replace("_", "").lower()
    aliases.update(GENERIC_FIELD_ALIASES.get(key, []))
    return sorted((item for item in aliases if item), key=lambda item: (-len(item), item))


def extract_catalog(docx_path: Path) -> dict[str, Any]:
    document = Document(docx_path)
    current_domain: tuple[str, str] | None = None
    recent: list[str] = []
    table_index = 0
    table_records: list[dict[str, Any]] = []
    option_values: dict[str, str] = {}

    for block in iter_blocks(document):
        if isinstance(block, Paragraph):
            text = clean_text(block.text)
            if text:
                current_domain = detect_domain(text, current_domain)
                recent = (recent + [text])[-12:]
            continue

        fields, raw_rows, has_header = extract_fields(block)
        if raw_rows and len(raw_rows[0]) >= 2 and raw_rows[0][0] == "OptionName":
            for row in raw_rows[1:]:
                if row and row[0]:
                    option_values[row[0]] = row[1] if len(row) > 1 else ""
            table_index += 1
            continue

        name, title = choose_table_title(recent)
        domain_key, domain_label = current_domain or ("unknown", "未分类")
        record = {
            "name": name,
            "title": title,
            "label": chinese_title(title, name),
            "domain": domain_key,
            "domain_label": domain_label,
            "source_table_index": table_index,
            "has_explicit_header": has_header,
            "fields": fields,
        }
        table_records.append(record)
        table_index += 1

    merged: dict[str, dict[str, Any]] = {}
    for table in table_records:
        key = table["name"].lower()
        if key not in merged:
            merged[key] = table
            table["duplicate_source_indices"] = []
            continue
        existing = merged[key]
        existing["duplicate_source_indices"].append(table["source_table_index"])
        known = {field["name"].lower() for field in existing["fields"]}
        existing["fields"].extend(field for field in table["fields"] if field["name"].lower() not in known)

    tables = list(merged.values())
    for table in tables:
        serial_field = next(
            (field for field in table["fields"] if field["name"].lower() == "serialno"),
            None,
        )
        if serial_field is None:
            table["fields"].append(
                {
                    "name": "SerialNo",
                    "type": "bigint",
                    "nullable": "Not null",
                    "default": "IDENTITY",
                    "key": "",
                    "description": "排序用自增序号（设计书通用修改）",
                    "source": "global_document_rule",
                }
            )
        else:
            serial_field["source_type"] = serial_field.get("type", "UNKNOWN")
            serial_field["type"] = "bigint"
            serial_field["nullable"] = "Not null"
            serial_field["default"] = "IDENTITY"
            serial_field["source"] = "global_document_rule"
        table["aliases"] = aliases_for_table(table)
        for field in table["fields"]:
            field["aliases"] = aliases_for_field(field)

    relations = infer_relations(tables)
    query_joins = build_query_joins(tables, relations)
    return {
        "name": "training_system_from_design_doc",
        "source_document": docx_path.name,
        "dialect": "sqlserver",
        "parameter_style": "qmark",
        "domains": [
            {"name": key, "label": label, "aliases": list(aliases)}
            for key, label, aliases in DOMAIN_PATTERNS
        ],
        "tables": tables,
        "relations": relations,
        "query_joins": query_joins,
        "configuration_options": option_values,
        "extraction": {
            "document_pages": 53,
            "document_table_objects": table_index,
            "unique_tables": len(tables),
            "fields": sum(len(table["fields"]) for table in tables),
        },
    }


def infer_relations(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary_fields: list[tuple[dict[str, Any], dict[str, str]]] = []
    for table in tables:
        for field in table["fields"]:
            if re.search(r"\bPK\b|主键", field.get("key", "") + " " + field.get("description", ""), re.I):
                primary_fields.append((table, field))
    relations: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for table in tables:
        for field in table["fields"]:
            evidence = field.get("key", "") + " " + field.get("description", "")
            if not re.search(r"\bFK\b|外键", evidence, re.I):
                continue
            field_key = field["name"].replace("_", "").lower()
            field_base = re.sub(r"id$", "", field_key)
            candidates: list[tuple[int, dict[str, Any], dict[str, str]]] = []
            for other, primary in primary_fields:
                if other["name"].lower() == table["name"].lower():
                    continue
                primary_key = primary["name"].replace("_", "").lower()
                table_key = re.sub(r"(?:info|detail|category)$", "", other["name"].replace("_", "").lower())
                score = 0
                if primary_key == field_key:
                    score += 60
                if field_base and field_base in table_key:
                    score += 50
                if other["label"] and other["label"].replace("表", "") in evidence:
                    score += 40
                if primary_key == "id":
                    score += 5
                if score:
                    candidates.append((score, other, primary))
            if not candidates:
                continue
            score, target_table, target_field = max(candidates, key=lambda item: item[0])
            relation_key = (table["name"], field["name"], target_table["name"], target_field["name"])
            if relation_key in seen:
                continue
            seen.add(relation_key)
            relations.append(
                {
                    "from": f"{table['name']}.{field['name']}",
                    "to": f"{target_table['name']}.{target_field['name']}",
                    "confidence": "high" if score >= 60 else "medium",
                    "evidence": clean_text(evidence)[:300],
                }
            )
    return relations


def build_query_joins(
    tables: list[dict[str, Any]], relations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Build a conservative join whitelist used by the SQL compiler.

    Document relations marked high-confidence are retained.  In addition,
    conventional foreign-key fields are linked only to a small set of known
    dimension/master tables.  This is deliberately separate from the broader
    inferred-relation list, which contains candidates that still need DBA QA.
    """
    table_lookup = {table["name"].lower(): table for table in tables}
    conventions = {
        "studentid": ("Student_Info", "Id"),
        "courseid": ("Course_Info", "Id"),
        "studyclassid": ("Study_Class_Info", "Id"),
        "offtrainid": ("OffTrain_Info", "Id"),
        "departmentid": ("Department", "ID"),
        "dutyid": ("Duty_Info", "ID"),
        "roleid": ("Role_Info", "Id"),
        "certificateid": ("Certificate_Info", "Id"),
        "repositoryid": ("Repository_Info", "Id"),
        "interestid": ("Interest_Info", "Id"),
        "gameid": ("GameInfo", "Id"),
        "skillid": ("Skill_Info", "Id"),
        "skilllevelid": ("Skill_Level_Info", "Id"),
        "newstypeid": ("News_Type_Info", "Id"),
    }
    rules: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add(left_table: str, left_field: str, right_table: str, right_field: str, source: str) -> None:
        key = (left_table.lower(), left_field.lower(), right_table.lower(), right_field.lower())
        reverse = (key[2], key[3], key[0], key[1])
        if key in seen or reverse in seen or left_table.lower() == right_table.lower():
            return
        left = table_lookup.get(left_table.lower())
        right = table_lookup.get(right_table.lower())
        if not left or not right:
            return
        if left_field.lower() not in {field["name"].lower() for field in left["fields"]}:
            return
        if right_field.lower() not in {field["name"].lower() for field in right["fields"]}:
            return
        seen.add(key)
        rules.append(
            {
                "left_table": left["name"],
                "left_field": next(field["name"] for field in left["fields"] if field["name"].lower() == left_field.lower()),
                "right_table": right["name"],
                "right_field": next(field["name"] for field in right["fields"] if field["name"].lower() == right_field.lower()),
                "source": source,
            }
        )

    for relation in relations:
        if relation.get("confidence") != "high":
            continue
        left_table, left_field = relation["from"].split(".", 1)
        right_table, right_field = relation["to"].split(".", 1)
        add(left_table, left_field, right_table, right_field, "document_high_confidence")

    for table in tables:
        for field in table["fields"]:
            key = field["name"].replace("_", "").lower()
            if key in conventions:
                target_table, target_field = conventions[key]
                add(table["name"], field["name"], target_table, target_field, "field_convention")

    # Explicitly documented navigation used for exam-score-to-student queries.
    add("clerk_kscj", "ExamStartId", "Exam_Start", "Id", "curated_design_route")
    return rules


def build_dictionary(catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": 2,
        "domains": {item["name"]: [item["label"], *item["aliases"]] for item in catalog["domains"]},
        "tables": {
            table["name"]: {
                "domain": table["domain"],
                "label": table["label"],
                "aliases": table["aliases"],
                "fields": {field["name"]: field["aliases"] for field in table["fields"]},
            }
            for table in catalog["tables"]
        },
        "operators": {
            "list": ["查询", "列出", "显示", "查看", "明细", "记录"],
            "count": ["数量", "总数", "多少", "几条", "几人", "几门", "几个"],
            "sum": ["合计", "总和", "累计", "总计"],
            "avg": ["平均", "均值"],
            "max": ["最大", "最高", "最多"],
            "min": ["最小", "最低", "最少"],
            "group": ["按", "每个", "各个", "各", "分别"],
            "top_n": ["前", "排名", "top"],
        },
        "time": {
            "today": ["今天", "今日"],
            "yesterday": ["昨天", "昨日"],
            "this_month": ["本月", "这个月"],
            "last_month": ["上月", "上个月"],
            "this_year": ["今年", "本年度"],
            "last_year": ["去年", "上一年度"],
        },
        "entities": ENTITY_DEFINITIONS,
    }


def write_report(catalog: dict[str, Any], path: Path) -> None:
    type_unknown = [
        f"{table['name']}.{field['name']}"
        for table in catalog["tables"]
        for field in table["fields"]
        if field["type"] == "UNKNOWN"
    ]
    no_pk = [
        table["name"]
        for table in catalog["tables"]
        if not any(re.search(r"\bPK\b|主键", field.get("key", "") + " " + field.get("description", ""), re.I) for field in table["fields"])
    ]
    domains = Counter(table["domain_label"] for table in catalog["tables"])
    lines = [
        "# 数据库设计书提取报告",
        "",
        f"- 文档页数：{catalog['extraction']['document_pages']}",
        f"- Word表格对象：{catalog['extraction']['document_table_objects']}",
        f"- 唯一业务表：{catalog['extraction']['unique_tables']}",
        f"- 提取字段：{catalog['extraction']['fields']}",
        f"- 推断关系：{len(catalog['relations'])}",
        f"- 查询白名单关系：{len(catalog.get('query_joins', []))}",
        f"- 类型未知字段：{len(type_unknown)}",
        f"- 未明确主键表：{len(no_pk)}",
        "",
        "## 业务域覆盖",
        "",
        "| 业务域 | 表数 |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {label} | {count} |" for label, count in domains.items())
    lines.extend(["", "## 提取限制", ""])
    lines.extend(
        [
            "- 评分活动部分表格没有类型列，对应字段保留为 `UNKNOWN`。",
            "- 外键关系来自文档中的 FK 标记、字段名和说明推断，必须在连接真实数据库前核验。",
            "- 参数配置的两张 OptionName/OptionValue 表被识别为配置字典续表，不计为独立业务表。",
            "- 重复出现的同名表已合并，并保留 `duplicate_source_indices`。",
            "- 设计书把 `tk_lx` 标题写成“题库集表”，而字段说明定义为节（题库）；目录保留原始标题，查询词典使用“题库/节题库”消除歧义。",
            "- `Certificate_Info` 中 `ImageUrl`/`CreateTime` 等类型按设计书原样保留，不基于字段名擅自改型。",
            "- 所有表的 `SerialNo` 按设计书全局修改统一为 `bigint NOT NULL IDENTITY`，原始类型保存在 `source_type`。",
            "",
            "## 未明确主键的表",
            "",
            ", ".join(no_pk) if no_pk else "无",
            "",
            "## 类型未知字段",
            "",
            ", ".join(type_unknown) if type_unknown else "无",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    catalog = extract_catalog(args.docx)
    args.catalog.parent.mkdir(parents=True, exist_ok=True)
    args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    dictionary = build_dictionary(catalog)
    args.dictionary.parent.mkdir(parents=True, exist_ok=True)
    args.dictionary.write_text(json.dumps(dictionary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(catalog, args.report)
    print(json.dumps(catalog["extraction"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
