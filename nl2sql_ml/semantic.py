from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from .compositional import detect_compositional_query
from .kpi import detect_kpi_report, reject_unsupported_analytics
from .model import ModelBundle
from .schema import (
    date_fields,
    dimension_fields,
    find_join_path,
    is_numeric,
    is_safe_entity_path,
    join_rule_key,
    numeric_fields,
    reachable_tables,
    table_map,
)


_SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵汪祁毛禹狄米贝明臧计伏成戴宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉龚程嵇邢裴陆荣翁荀羊甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲台从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍却璩桑桂濮牛寿通边扈燕冀浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公"


class SemanticParser:
    def __init__(
        self,
        catalog: dict[str, Any],
        dictionary: dict[str, Any],
        models: ModelBundle,
        semantic_layer: dict[str, Any] | None = None,
    ):
        self.catalog = catalog
        self.dictionary = dictionary
        self.models = models
        self.semantic_layer = semantic_layer or {"facts": {}}
        self.tables = table_map(catalog)

    def parse(self, question: str, today: date | None = None) -> dict[str, Any]:
        text = self._normalize(question)
        if not text:
            raise ValueError("问题不能为空")
        if (
            "课件学习记录" in text
            and "学员课件学习记录" not in text
            and "课件登录" not in text
            and "学习会话" not in text
        ):
            raise ValueError(
                "“课件学习记录”在设计书中存在两种口径：Student_Courseware_Info学员课件汇总记录，"
                "以及Courseware_Login_Info课件学习会话；请明确需要哪一种"
            )
        today = today or date.today()
        report_plan = detect_kpi_report(question, text, self.catalog, today)
        if report_plan is not None:
            return report_plan
        compositional_plan = detect_compositional_query(
            question,
            text,
            self.semantic_layer,
            today,
            _SURNAMES,
            self._valid_person_name,
        )
        if compositional_plan is not None:
            return compositional_plan
        reject_unsupported_analytics(text)
        predictions = {
            target: self.models.predict(target, text)
            for target in ("intent", "domain", "table", "aggregation")
        }
        domain = self._domain(text, predictions["domain"][0])
        table_name, table_source = self._table(text, predictions["table"])
        if table_source == "model" and predictions["table"][1] < 0.05:
            raise ValueError(
                "目标事实表无法可靠识别，已拒绝生成SQL；请补充业务对象、指标口径或使用已审核语义视图"
            )
        table = self.tables[table_name]
        intent = self._intent(text, predictions["intent"][0])
        aggregation = self._aggregation(text) or predictions["aggregation"][0]
        metric = self._metric_field(text, table)
        metric_table = table_name if metric else None
        dimension, dimension_table, dimension_joins = self._dimension_field(
            text, table, intent
        )
        explicit_count = self._explicit_count(text)

        if intent == "count":
            aggregation = "count"
            metric = None
            metric_table = None
            dimension = None
            dimension_table = None
            dimension_joins = []
        elif intent == "list":
            aggregation = None
            metric = None
            metric_table = None
            dimension = None
            dimension_table = None
            dimension_joins = []
        elif intent in {"group_aggregate", "top_n"}:
            if explicit_count:
                aggregation = "count"
                metric = None
                metric_table = None
            elif intent == "top_n":
                if any(word in text for word in ("平均", "均值")):
                    aggregation = "avg"
                elif any(word in text for word in ("合计", "总和", "累计")):
                    aggregation = "sum"
                else:
                    aggregation = "sum" if metric is not None else "count"
            elif metric is None:
                aggregation = "count"
            if dimension is None:
                candidates = dimension_fields(table)
                dimension = candidates[0] if candidates else None
                dimension_table = table_name if dimension else None
        elif intent == "aggregate" and metric is None:
            candidates = numeric_fields(table)
            metric = candidates[0] if candidates else None
            metric_table = table_name if metric else None
            if metric is None:
                aggregation = "count"

        excluded = (
            dimension["name"]
            if dimension and dimension_table == table_name
            else None
        )
        filters = self._filters(text, table, excluded=excluded)
        entity_filters, entity_joins, entity_sources, unresolved = self._entity_filters(
            text, table_name
        )
        if unresolved:
            values = "、".join(unresolved)
            raise ValueError(f"识别到筛选实体“{values}”，但没有安全、明确的关联路径")
        filters = self._deduplicate_filters([*filters, *entity_filters])
        joins = self._deduplicate_joins([*dimension_joins, *entity_joins])

        date_start, date_end, time_expression = self._time_range(text, today)
        time_field = self._time_field(text, table) if date_start or date_end else None
        order = "asc" if any(word in text for word in ("最低", "最少", "最小", "倒数")) else "desc"
        limit = self._limit(text) if intent == "top_n" else (100 if intent == "list" else None)
        warnings: list[str] = []
        if table_source == "model":
            warnings.append("表名未精确匹配业务词典，使用了模型预测")
            if predictions["table"][1] < 0.25:
                warnings.append("数据表预测置信度较低，请确认目标表")
        if joins:
            warnings.append(f"使用了{len(joins)}条白名单关联，请在真实数据库核验结果")
        if intent in {"aggregate", "group_aggregate", "top_n"} and aggregation != "count" and metric is None:
            warnings.append("没有识别到可聚合数值字段")
        if intent in {"group_aggregate", "top_n"} and dimension is None:
            warnings.append("没有识别到分组字段")

        return {
            "question": question,
            "intent": intent,
            "domain": domain,
            "table": table_name,
            "metric_column": metric["name"] if metric else None,
            "metric_table": metric_table,
            "dimension_column": dimension["name"] if dimension else None,
            "dimension_table": dimension_table,
            "aggregation": aggregation,
            "filters": filters,
            "joins": joins,
            "entities": entity_sources,
            "unresolved_entities": [],
            "time_field": time_field["name"] if time_field else None,
            "date_start": date_start,
            "date_end": date_end,
            "time_expression": time_expression,
            "limit": limit,
            "order": order,
            "confidence": {target: round(values[1], 4) for target, values in predictions.items()},
            "sources": {"table": table_source},
            "warnings": warnings,
        }

    @staticmethod
    def _normalize(text: str) -> str:
        # Preserve the Chinese enumeration delimiter “、” because it carries
        # list structure for multi-entity filters such as “张三、李四、王五”.
        return re.sub(r"[\s，。！？,!?]", "", text.strip().lower())

    def _domain(self, text: str, predicted: str) -> str:
        matches: list[tuple[int, str]] = []
        for name, aliases in self.dictionary.get("domains", {}).items():
            for alias in aliases:
                normalized = self._normalize(alias)
                if normalized and normalized in text:
                    matches.append((len(normalized), name))
        return max(matches)[1] if matches else predicted

    def _table(self, text: str, prediction: tuple[str, float, dict[str, float]]) -> tuple[str, str]:
        if re.search(r"[\u4e00-\u9fffA-Za-z0-9_-]{2,20}班(?:收到|对应)?的报名申请", text):
            return "Study_Class_Apply_Info", "dictionary"
        predicted, _, details = prediction
        matches: list[tuple[int, float, str]] = []
        for name, item in self.dictionary["tables"].items():
            for alias in item.get("aliases", []):
                normalized = self._normalize(alias)
                if normalized and len(normalized) >= 2 and normalized in text:
                    matches.append((len(normalized), details.get(name, 0.0), name))
        if not matches:
            return predicted, "model"
        best = max(matches)
        return best[2], "dictionary"

    @staticmethod
    def _intent(text: str, predicted: str) -> str:
        if re.search(r"(?:前[一二三五十\d]+|top\d+|排名)", text):
            return "top_n"
        if any(word in text for word in ("每个", "各个", "各", "分别", "分组", "按")):
            return "group_aggregate"
        if SemanticParser._explicit_count(text):
            return "count"
        if any(word in text for word in ("合计", "总和", "累计", "平均", "均值", "最大", "最小", "最高", "最低")):
            return "aggregate"
        if any(
            word in text
            for word in (
                "查询",
                "列出",
                "显示",
                "查看",
                "调出",
                "调取",
                "明细",
                "记录",
                "列表",
                "名单",
                "清单",
            )
        ):
            return "list"
        return predicted

    @staticmethod
    def _explicit_count(text: str) -> bool:
        return bool(re.search(r"(?:多少条|多少个|多少人|几条|几人|总数|记录数|数量)", text))

    def _aggregation(self, text: str) -> str | None:
        operator = self.dictionary.get("operators", {})
        for name in ("avg", "sum", "max", "min"):
            if any(self._normalize(word) in text for word in operator.get(name, [])):
                return name
        return None

    def _metric_field(self, text: str, table: dict[str, Any]) -> dict[str, Any] | None:
        return self._field_match(
            text,
            [field for field in table["fields"] if is_numeric(field)],
            analytical=False,
            table_name=table["name"],
        )

    def _dimension_field(
        self, text: str, table: dict[str, Any], intent: str
    ) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]]]:
        if intent not in {"group_aggregate", "top_n"}:
            return None, None, []
        best_field, best_score = self._best_field_match(
            text, dimension_fields(table), analytical=True, table_name=table["name"]
        )
        best_table = table["name"] if best_field else None
        best_path: list[dict[str, Any]] = []
        for related_name, path in reachable_tables(
            self.catalog, table["name"], max_hops=2
        ).items():
            if related_name == table["name"]:
                continue
            if not is_safe_entity_path(table["name"], related_name, path):
                continue
            field, score = self._best_field_match(
                text,
                dimension_fields(self.tables[related_name]),
                analytical=True,
                table_name=related_name,
            )
            score -= len(path)
            if field and score > best_score:
                best_field, best_score = field, score
                best_table, best_path = related_name, path
        return best_field, best_table, best_path

    def _field_match(
        self,
        text: str,
        candidates: list[dict[str, Any]],
        analytical: bool,
        table_name: str | None = None,
    ) -> dict[str, Any] | None:
        return self._best_field_match(text, candidates, analytical, table_name)[0]

    def _best_field_match(
        self,
        text: str,
        candidates: list[dict[str, Any]],
        analytical: bool,
        table_name: str | None = None,
    ) -> tuple[dict[str, Any] | None, int]:
        matches: list[tuple[int, int, dict[str, Any]]] = []
        for field in candidates:
            dictionary_aliases = (
                self.dictionary.get("tables", {})
                .get(table_name or "", {})
                .get("fields", {})
                .get(field["name"], [])
            )
            for alias in dict.fromkeys([*field.get("aliases", []), *dictionary_aliases]):
                normalized = self._normalize(alias)
                variants = {normalized}
                if "的" in normalized:
                    suffix = normalized.rsplit("的", 1)[-1]
                    if len(suffix) >= 2:
                        variants.add(suffix)
                    collapsed = normalized.replace("的", "")
                    variants.add(collapsed)
                    for tail in ("评定", "信息", "标识"):
                        if collapsed.endswith(tail) and len(collapsed) > len(tail) + 1:
                            variants.add(collapsed[: -len(tail)])
                for variant in variants:
                    start = text.find(variant)
                    if start < 0 or len(variant) < 1:
                        continue
                    score = len(variant)
                    prefix = text[max(0, start - 8) : start]
                    if analytical and re.search(r"(?:按|每个|各个|各|分别|前\d+个)$", prefix):
                        score += 100
                    matches.append((score, len(variant), field))
        if not matches:
            return None, -1
        best = max(matches, key=lambda item: (item[0], item[1], item[2]["name"]))
        return best[2], best[0]

    def _filters(
        self, text: str, table: dict[str, Any], excluded: str | None
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for field in table["fields"]:
            if field["name"] == excluded:
                continue
            dictionary_aliases = (
                self.dictionary.get("tables", {})
                .get(table["name"], {})
                .get("fields", {})
                .get(field["name"], [])
            )
            for alias in dict.fromkeys([*field.get("aliases", []), *dictionary_aliases]):
                normalized = self._normalize(alias)
                if not normalized or normalized not in text:
                    continue
                pattern = re.escape(normalized) + r"(?:为|是|等于|=)([^的且并与，。]{1,30})"
                match = re.search(pattern, text)
                if not match:
                    continue
                value: Any = match.group(1)
                if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
                    value = float(value) if "." in value else int(value)
                results.append(
                    {"table": table["name"], "field": field["name"], "operator": "=", "value": value}
                )
                break
        return results

    def _entity_filters(
        self, text: str, primary_table: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        filters: list[dict[str, Any]] = []
        joins: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        unresolved: list[str] = []
        entities = self.dictionary.get("entities", {})
        for entity_type, spec in entities.items():
            value = self._extract_entity_value(text, entity_type, spec)
            if value is None:
                continue
            target_table = spec["table"]
            path = find_join_path(
                self.catalog, primary_table, target_table, max_hops=3
            )
            if path is None or not is_safe_entity_path(primary_table, target_table, path):
                unresolved.append(value)
                continue
            joins.extend(path)
            filters.append(
                {
                    "table": target_table,
                    "field": spec["field"],
                    "operator": "=",
                    "value": value,
                    "entity_type": entity_type,
                }
            )
            sources.append(
                {
                    "type": entity_type,
                    "value": value,
                    "table": target_table,
                    "field": spec["field"],
                }
            )
        unsupported = re.search(
            rf"([{_SURNAMES}][\u4e00-\u9fff]{{1,3}}?)(创建|审核|发布|判卷|管理)的",
            text,
        )
        if unsupported:
            unsupported_name = self._clean_entity_value(unsupported.group(1))
            if self._valid_person_name(unsupported_name) and not any(
                item["value"] == unsupported_name for item in sources
            ):
                unresolved.append(f"{unsupported_name}{unsupported.group(2)}")
        return filters, joins, sources, unresolved

    def _extract_entity_value(
        self, text: str, entity_type: str, spec: dict[str, Any]
    ) -> str | None:
        for alias in sorted(spec.get("aliases", []), key=len, reverse=True):
            match = re.search(
                re.escape(self._normalize(alias)) + r"(?:为|是|等于|=)([^的且并与]{1,30})",
                text,
            )
            if match:
                return self._clean_entity_value(match.group(1))
        if entity_type == "person_name":
            for pattern in (
                rf"(?:查询|查看|显示|列出|调出|调取|统计|请问|请把|把|帮我|麻烦|给我|且)(?P<value>[{_SURNAMES}][\u4e00-\u9fff]{{1,3}}?)(?=(?:所有|全部)?(?:参加考试后|参加|报名|学习|负责|获得|对应)?的)(?:所有|全部)?(?:参加考试后|参加|报名|学习|负责|获得|对应)?的",
                rf"^(?!查询|查看|显示|列出|调出|调取|统计|请问|请把|把|帮我|麻烦|给我)(?P<value>[{_SURNAMES}][\u4e00-\u9fff]{{1,3}}?)(?=(?:所有|全部)?(?:参加考试后|参加|报名|学习|负责|获得|对应)?的)(?:所有|全部)?(?:参加考试后|参加|报名|学习|负责|获得|对应)?的",
                rf"^(?P<value>[{_SURNAMES}][\u4e00-\u9fff]{{1,3}}?)(?=(?:都|曾经|曾)?(?:参加过|报名过|学习过|参加|报名|学习))",
                rf"(?P<value>[{_SURNAMES}][\u4e00-\u9fff]{{1,3}}?)(?=状态(?:为|是|等于|=))",
            ):
                match = re.search(pattern, text)
                if match:
                    value = self._clean_entity_value(match.group("value"))
                    if self._valid_person_name(value):
                        return value
            return None
        if entity_type == "user_name":
            match = re.search(
                r"(?:学员账号|登录账号|账号|账户|用户名|登录名)"
                r"(?P<value>[A-Za-z0-9_.-]{2,50})(?=的|对应|$)",
                text,
            )
            if match:
                return match.group("value")
        if entity_type == "course_name":
            for pattern in (
                r"(?:参加|学习|选修)(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,20})课程(?:的|中)",
                r"(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,20})课程(?:所有|全部|对应)?的(?:学员|员工|人员|报名|成绩|记录|学习日志|日志)",
            ):
                match = re.search(pattern, text)
                if match:
                    value = self._clean_entity_value(match.group("value"))
                    if value not in {"查询", "查看", "显示", "统计", "课程"}:
                        return value
        if entity_type == "study_class_name":
            for pattern in (
                r"(?:参加|报名)(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,20})(?:学习班|培训班)(?:的|中)",
                r"(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,20}班)(?=(?:收到|对应)?的报名申请)",
            ):
                match = re.search(pattern, text)
                if match:
                    return self._clean_entity_value(match.group("value"))
        if entity_type == "department_name":
            match = re.search(
                r"(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{1,12}部)(?:所有|全部)?(?:的)?(?:学员|员工|人员)",
                text,
            )
            if match:
                return self._clean_entity_value(match.group("value"))
        if entity_type == "skill_name":
            match = re.search(
                r"(?:对应|关于)(?:的)?(?P<value>[\u4e00-\u9fffA-Za-z0-9_-]{2,30}?)(?:能力|技能)(?=记录|明细|$)",
                text,
            )
            if match:
                value = self._clean_entity_value(match.group("value"))
                if value not in {"员工", "学员", "人员", "个人", "岗位"}:
                    return value
        return None

    @staticmethod
    def _clean_entity_value(value: str) -> str:
        value = re.sub(r"^(?:查询|查看|显示|列出|统计|参加|学习|选修)+", "", value)
        value = re.sub(r"(?:这门|该门)$", "", value)
        return value.strip("的")

    @staticmethod
    def _valid_person_name(value: str) -> bool:
        blocked = (
            "查询",
            "查看",
            "请查看",
            "筛选",
            "教务",
            "后台",
            "全部",
            "所有",
            "考试",
            "成绩",
            "状态",
            "课程",
            "学习",
            "报名",
            "记录",
            "本月",
            "上月",
            "今年",
            "去年",
            "创建",
            "群组",
            "积分",
            "岗位",
            "部门",
            "能力",
            "游戏",
            "课件",
            "题型",
            "题库",
            "新闻",
            "邮件",
            "角色",
            "证书",
        )
        return (
            2 <= len(value) <= 4
            and value[0] in _SURNAMES
            and not any(word in value for word in blocked)
        )

    @staticmethod
    def _deduplicate_filters(filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: dict[tuple[str, str], dict[str, Any]] = {}
        for item in filters:
            unique.setdefault((item.get("table", ""), item["field"]), item)
        return list(unique.values())

    @staticmethod
    def _deduplicate_joins(joins: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: dict[Any, dict[str, Any]] = {}
        for rule in joins:
            unique.setdefault(join_rule_key(rule), rule)
        return list(unique.values())

    def _time_field(self, text: str, table: dict[str, Any]) -> dict[str, Any] | None:
        candidates = date_fields(table)
        matched = self._field_match(
            text, candidates, analytical=False, table_name=table["name"]
        )
        if matched:
            return matched
        priorities = (
            "createdtime",
            "createtime",
            "applytime",
            "applydate",
            "begintime",
            "starttime",
        )
        by_name = {field["name"].lower(): field for field in candidates}
        return next((by_name[name] for name in priorities if name in by_name), None) or (
            candidates[0] if candidates else None
        )

    @staticmethod
    def _limit(text: str) -> int:
        for pattern in (r"前(\d+)", r"top(\d+)", r"(\d+)个", r"(\d+)名"):
            match = re.search(pattern, text, re.I)
            if match:
                return max(1, min(int(match.group(1)), 1000))
        chinese = {"三": 3, "五": 5, "十": 10, "二十": 20}
        for word, value in chinese.items():
            if f"前{word}" in text or f"{word}个" in text:
                return value
        return 10

    @staticmethod
    def _time_range(text: str, today: date) -> tuple[str | None, str | None, str | None]:
        explicit = re.search(
            r"(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})日?(?:到|至|-)(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})日?",
            text,
        )
        if explicit:
            start = date(*map(int, explicit.groups()[:3]))
            end = date(*map(int, explicit.groups()[3:])) + timedelta(days=1)
            return start.isoformat(), end.isoformat(), explicit.group(0)
        calendar_year = re.search(r"(20\d{2})(?:年度|全年|年)", text)
        if calendar_year:
            year = int(calendar_year.group(1))
            return date(year, 1, 1).isoformat(), date(year + 1, 1, 1).isoformat(), calendar_year.group(0)
        days = re.search(r"(?:最近|近|过去)(\d+)天", text)
        if days:
            number = max(1, int(days.group(1)))
            return (today - timedelta(days=number - 1)).isoformat(), (today + timedelta(days=1)).isoformat(), days.group(0)
        if "今天" in text:
            return today.isoformat(), (today + timedelta(days=1)).isoformat(), "今天"
        if "昨天" in text:
            return (today - timedelta(days=1)).isoformat(), today.isoformat(), "昨天"
        if "本月" in text or "这个月" in text:
            start = today.replace(day=1)
            end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            return start.isoformat(), end.isoformat(), "本月"
        if "上个月" in text or "上月" in text:
            end = today.replace(day=1)
            start = (end - timedelta(days=1)).replace(day=1)
            return start.isoformat(), end.isoformat(), "上个月"
        if "今年" in text:
            return date(today.year, 1, 1).isoformat(), date(today.year + 1, 1, 1).isoformat(), "今年"
        if "去年" in text:
            return date(today.year - 1, 1, 1).isoformat(), date(today.year, 1, 1).isoformat(), "去年"
        return None, None, None
