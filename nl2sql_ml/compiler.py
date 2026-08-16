from __future__ import annotations

from datetime import date
from typing import Any

from .compositional import EXAM_SCORE_AGGREGATE_QUERY, EXAM_SCORE_RANKING_QUERY
from .kpi import MONTHLY_DEPARTMENT_LEARNING_REPORT
from .schema import (
    date_fields,
    field_map,
    join_rule_key,
    primary_key,
    quote_identifier,
    table_map,
)


class SQLCompileError(ValueError):
    pass


class SQLCompiler:
    """Compile a validated semantic plan into parameterized SQL Server SELECT."""

    def __init__(
        self,
        catalog: dict[str, Any],
        semantic_layer: dict[str, Any] | None = None,
    ):
        self.catalog = catalog
        self.semantic_layer = semantic_layer or {"facts": {}}
        self.tables = table_map(catalog)
        self.dialect = catalog.get("dialect", "sqlserver")
        self.allowed_joins = {
            join_rule_key(rule): rule for rule in catalog.get("query_joins", [])
        }

    def compile(self, plan: dict[str, Any]) -> tuple[str, list[Any]]:
        table_name = plan.get("table")
        if table_name not in self.tables:
            raise SQLCompileError(f"未知表: {table_name}")
        if plan.get("report_type"):
            return self._compile_kpi_report(plan)
        table = self.tables[table_name]
        intent = plan.get("intent")
        limit = max(1, min(int(plan.get("limit") or 100), 1000))

        aliases, join_sql = self._prepare_joins(table_name, plan.get("joins", []))
        qualified = bool(join_sql)
        metric_table = plan.get("metric_table") or table_name
        dimension_table = plan.get("dimension_table") or table_name
        metric_name = plan.get("metric_column")
        dimension_name = plan.get("dimension_column")
        aggregation = plan.get("aggregation")
        metric = self._field(metric_table, metric_name) if metric_name else None
        dimension = self._field(dimension_table, dimension_name) if dimension_name else None
        self._require_joined(metric_table, aliases)
        self._require_joined(dimension_table, aliases)

        select_prefix = "SELECT"
        if intent in {"list", "top_n"}:
            select_prefix += f" TOP ({limit})"

        group_by = ""
        order_by = ""
        if intent == "list":
            select_items = [
                self._column(field["name"], table_name, aliases, qualified)
                for field in self._list_fields(table)
            ]
        elif intent == "count":
            select_items = ["COUNT_BIG(*) AS [record_count]"]
        elif intent in {"aggregate", "group_aggregate", "top_n"}:
            if not metric and aggregation != "count":
                raise SQLCompileError("聚合查询缺少数值字段")
            aggregation = aggregation or "count"
            expression, alias = self._aggregate(
                metric, aggregation, metric_table, aliases, qualified
            )
            select_items = [f"{expression} AS {quote_identifier(alias, self.dialect)}"]
            if intent in {"group_aggregate", "top_n"}:
                if not dimension:
                    raise SQLCompileError("分组查询缺少维度字段")
                dimension_sql = self._column(
                    dimension["name"], dimension_table, aliases, qualified
                )
                select_items.insert(
                    0,
                    f"{dimension_sql} AS {quote_identifier(dimension['name'], self.dialect)}",
                )
                group_by = f" GROUP BY {dimension_sql}"
            if intent == "top_n":
                direction = "ASC" if plan.get("order") == "asc" else "DESC"
                order_by = f" ORDER BY {quote_identifier(alias, self.dialect)} {direction}"
        else:
            raise SQLCompileError(f"未知查询意图: {intent}")

        params: list[Any] = []
        where: list[str] = []
        for item in plan.get("filters", []):
            filter_table = item.get("table") or table_name
            self._require_joined(filter_table, aliases)
            field = self._field(filter_table, item.get("field"))
            operator = item.get("operator", "=")
            if operator == "IN":
                values = item.get("value")
                if not isinstance(values, list) or not 1 <= len(values) <= 100:
                    raise SQLCompileError("IN筛选值必须是1至100个元素的列表")
                placeholders = ", ".join("?" for _ in values)
                where.append(
                    f"{self._column(field['name'], filter_table, aliases, qualified)} IN ({placeholders})"
                )
                params.extend(values)
                continue
            if operator not in {"=", ">", ">=", "<", "<=", "<>", "LIKE"}:
                raise SQLCompileError(f"不允许的筛选操作符: {operator}")
            where.append(
                f"{self._column(field['name'], filter_table, aliases, qualified)} {operator} ?"
            )
            params.append(item.get("value"))

        time_field_name = plan.get("time_field")
        if (plan.get("date_start") or plan.get("date_end")) and not time_field_name:
            candidates = date_fields(table)
            time_field_name = candidates[0]["name"] if candidates else None
        if time_field_name:
            time_field = self._field(table_name, time_field_name)
            if plan.get("date_start"):
                where.append(
                    f"{self._column(time_field['name'], table_name, aliases, qualified)} >= ?"
                )
                params.append(plan["date_start"])
            if plan.get("date_end"):
                where.append(
                    f"{self._column(time_field['name'], table_name, aliases, qualified)} < ?"
                )
                params.append(plan["date_end"])

        source = quote_identifier(table_name, self.dialect)
        if qualified:
            source += f" AS {quote_identifier(aliases[table_name], self.dialect)}"
        sql = f"{select_prefix} {', '.join(select_items)} FROM {source}{join_sql}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += group_by + order_by + ";"
        if not sql.upper().startswith("SELECT") or ";" in sql[:-1]:
            raise SQLCompileError("编译器只允许生成一条SELECT")
        return sql, params

    def _compile_kpi_report(self, plan: dict[str, Any]) -> tuple[str, list[Any]]:
        report_type = plan.get("report_type")
        if report_type == EXAM_SCORE_AGGREGATE_QUERY:
            return self._compile_exam_score_query(plan)
        if report_type == EXAM_SCORE_RANKING_QUERY:
            return self._compile_exam_score_ranking(plan)
        if report_type != MONTHLY_DEPARTMENT_LEARNING_REPORT:
            raise SQLCompileError(f"未审核的报表类型: {report_type}")
        if plan.get("table") != "Student_Course_Log":
            raise SQLCompileError("部门逐月人均学习时长报表的事实表不正确")

        for table_name, fields in {
            "Student_Info": ("Id", "Department", "Status"),
            "Student_Course_Log": ("StudentId", "BeginTime", "EndTime"),
        }.items():
            for field_name in fields:
                self._field(table_name, field_name)
        join = {
            "left_table": "Student_Course_Log",
            "left_field": "StudentId",
            "right_table": "Student_Info",
            "right_field": "Id",
        }
        if join_rule_key(join) not in self.allowed_joins:
            raise SQLCompileError("学习日志到学员表的关联不在白名单中")

        try:
            start = date.fromisoformat(str(plan.get("date_start")))
            end = date.fromisoformat(str(plan.get("date_end")))
        except ValueError as exc:
            raise SQLCompileError("年度报表日期范围无效") from exc
        if start != date(start.year, 1, 1) or end != date(start.year + 1, 1, 1):
            raise SQLCompileError("年度报表必须使用完整自然年范围")

        student = "[s]"
        log = "[l]"
        monthly_columns: list[str] = []
        for month in range(1, 13):
            duration = (
                f"CASE WHEN MONTH({log}.[BeginTime]) = {month} "
                f"AND {log}.[EndTime] >= {log}.[BeginTime] "
                f"THEN CAST(DATEDIFF(SECOND, {log}.[BeginTime], {log}.[EndTime]) AS bigint) "
                f"ELSE CAST(0 AS bigint) END"
            )
            expression = (
                f"ROUND(COALESCE(CAST(SUM({duration}) AS decimal(38,2)) "
                f"/ NULLIF(COUNT(DISTINCT {student}.[Id]), 0) / 3600.0, 0), 2) "
                f"AS [{month}月人均学习时长_小时]"
            )
            monthly_columns.append(expression)

        sql = (
            f"SELECT {student}.[Department] AS [Department], "
            + ", ".join(monthly_columns)
            + f" FROM [Student_Info] AS {student}"
            + f" LEFT JOIN [Student_Course_Log] AS {log}"
            + f" ON {student}.[Id] = {log}.[StudentId]"
            + f" AND {log}.[BeginTime] >= ? AND {log}.[BeginTime] < ?"
            + f" WHERE {student}.[Status] = ?"
            + f" GROUP BY {student}.[Department]"
            + f" ORDER BY {student}.[Department] ASC;"
        )
        if not sql.upper().startswith("SELECT") or ";" in sql[:-1]:
            raise SQLCompileError("编译器只允许生成一条SELECT")
        return sql, [start.isoformat(), end.isoformat(), 1]

    def _compile_exam_score_query(self, plan: dict[str, Any]) -> tuple[str, list[Any]]:
        fact = self.semantic_layer.get("facts", {}).get("exam_score")
        if not fact:
            raise SQLCompileError("业务语义层没有定义exam_score事实")
        if plan.get("table") != fact.get("base_table"):
            raise SQLCompileError("考试成绩查询的事实表不正确")
        aggregation = plan.get("aggregation")
        measure = fact.get("measures", {}).get("score", {})
        if aggregation not in measure.get("allowed_aggregations", []):
            raise SQLCompileError(f"考试成绩不支持聚合方式: {aggregation}")
        for table_name, fields in {
            "clerk_kscj": ("Cj", "ExamStartId", "Tk_cl_id", "clerk_ks_btime", "Clerk_ks_status"),
            "Exam_Start": ("Id", "StudentId"),
            "Student_Info": ("Id", "ActualName"),
            "tk_cl": ("Tk_cl_id", "SiteID", "SiteType"),
            "Course_Info": ("Id", "Name"),
        }.items():
            for field_name in fields:
                self._field(table_name, field_name)

        ast_filters = plan.get("semantic_ast", {}).get("filters", {})
        people = ast_filters.get("student_name", {}).get("values", [])
        if (
            not isinstance(people, list)
            or not 1 <= len(people) <= 20
            or not all(isinstance(value, str) and value for value in people)
        ):
            raise SQLCompileError("考试成绩查询的学员列表无效")
        course_name = ast_filters.get("course_name")
        if course_name is not None and not isinstance(course_name, str):
            raise SQLCompileError("课程名称筛选值无效")

        required_keys = [
            join_rule_key(
                {
                    "left_table": "clerk_kscj",
                    "left_field": "ExamStartId",
                    "right_table": "Exam_Start",
                    "right_field": "Id",
                }
            ),
            join_rule_key(
                {
                    "left_table": "Exam_Start",
                    "left_field": "StudentId",
                    "right_table": "Student_Info",
                    "right_field": "Id",
                }
            ),
        ]
        if course_name:
            required_keys.append(
                join_rule_key(
                    {
                        "left_table": "clerk_kscj",
                        "left_field": "Tk_cl_id",
                        "right_table": "tk_cl",
                        "right_field": "Tk_cl_id",
                    }
                )
            )
        if any(key not in self.allowed_joins for key in required_keys):
            raise SQLCompileError("考试成绩查询所需的基础关联不在白名单中")

        placeholders = ", ".join("?" for _ in people)
        function = aggregation.upper()
        alias = {"max": "max_score", "min": "min_score", "avg": "avg_score"}[aggregation]
        sql = (
            f"SELECT [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], "
            f"{function}([k].[Cj]) AS [{alias}] "
            "FROM [clerk_kscj] AS [k] "
            "INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] "
            "INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id]"
        )
        params: list[Any] = list(people)
        where = [f"[s].[ActualName] IN ({placeholders})"]
        if course_name:
            sql += (
                " INNER JOIN [tk_cl] AS [p] ON [k].[Tk_cl_id] = [p].[Tk_cl_id]"
                " INNER JOIN [Course_Info] AS [c]"
                " ON CONVERT(varchar(50), [p].[SiteID]) = [c].[Id]"
                " AND [p].[SiteType] IN (1, 3)"
            )
            where.append("[c].[Name] = ?")
            params.append(course_name)
        date_start = plan.get("date_start")
        date_end = plan.get("date_end")
        if bool(date_start) != bool(date_end):
            raise SQLCompileError("考试成绩查询的日期范围不完整")
        if date_start and date_end:
            try:
                start = date.fromisoformat(str(date_start))
                end = date.fromisoformat(str(date_end))
            except ValueError as exc:
                raise SQLCompileError("考试成绩查询的日期范围无效") from exc
            if start >= end:
                raise SQLCompileError("考试成绩查询的日期范围顺序无效")
            where.extend(("[k].[clerk_ks_btime] >= ?", "[k].[clerk_ks_btime] < ?"))
            params.extend((start.isoformat(), end.isoformat()))
        where.extend(("[k].[Clerk_ks_status] = ?", "[k].[Cj] IS NOT NULL"))
        params.append(1)
        sql += (
            " WHERE " + " AND ".join(where)
            + " GROUP BY [s].[Id], [s].[ActualName]"
            + " ORDER BY [s].[ActualName] ASC;"
        )
        if not sql.upper().startswith("SELECT") or ";" in sql[:-1]:
            raise SQLCompileError("编译器只允许生成一条SELECT")
        return sql, params

    def _compile_exam_score_ranking(self, plan: dict[str, Any]) -> tuple[str, list[Any]]:
        fact = self.semantic_layer.get("facts", {}).get("exam_score")
        if not fact or plan.get("table") != fact.get("base_table"):
            raise SQLCompileError("考试成绩排名的事实表不正确")
        ast = plan.get("semantic_ast", {})
        if ast.get("type") != "ranking_query" or ast.get("fact") != "exam_score":
            raise SQLCompileError("考试成绩排名缺少有效语义AST")
        aggregation = plan.get("aggregation")
        measure = fact.get("measures", {}).get("score", {})
        if aggregation not in measure.get("allowed_aggregations", []):
            raise SQLCompileError(f"考试成绩排名不支持聚合方式: {aggregation}")
        try:
            limit = int(plan.get("limit"))
        except (TypeError, ValueError) as exc:
            raise SQLCompileError("考试成绩排名数量无效") from exc
        if not 1 <= limit <= 1000:
            raise SQLCompileError("考试成绩排名数量必须为1至1000")
        order = plan.get("order")
        if order not in {"asc", "desc"}:
            raise SQLCompileError("考试成绩排名方向无效")

        filters = ast.get("filters", {})
        course_scope = filters.get("course_scope")
        course_name = filters.get("course_name")
        department = filters.get("department")
        if course_scope not in {"specific", "all_courses", "all_exams"}:
            raise SQLCompileError("考试成绩排名课程范围无效")
        if course_scope == "specific" and not isinstance(course_name, str):
            raise SQLCompileError("指定课程排名缺少课程名称")
        if department is not None and not isinstance(department, str):
            raise SQLCompileError("部门筛选值无效")

        for table_name, fields in {
            "clerk_kscj": ("Cj", "ExamStartId", "Tk_cl_id", "clerk_ks_btime", "Clerk_ks_status"),
            "Exam_Start": ("Id", "StudentId"),
            "Student_Info": ("Id", "ActualName", "Department"),
            "tk_cl": ("Tk_cl_id", "SiteID", "SiteType"),
            "Course_Info": ("Id", "Name"),
        }.items():
            for field_name in fields:
                self._field(table_name, field_name)

        function = aggregation.upper()
        alias = {"max": "max_score", "min": "min_score", "avg": "avg_score"}[aggregation]
        sql = (
            f"SELECT TOP ({limit}) [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], "
            f"{function}([k].[Cj]) AS [{alias}] "
            "FROM [clerk_kscj] AS [k] "
            "INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] "
            "INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id]"
        )
        if course_scope != "all_exams":
            sql += (
                " INNER JOIN [tk_cl] AS [p] ON [k].[Tk_cl_id] = [p].[Tk_cl_id]"
                " INNER JOIN [Course_Info] AS [c]"
                " ON CONVERT(varchar(50), [p].[SiteID]) = [c].[Id]"
                " AND [p].[SiteType] IN (1, 3)"
            )

        params: list[Any] = []
        where: list[str] = []
        if department:
            where.append("[s].[Department] = ?")
            params.append(department)
        if course_name:
            where.append("[c].[Name] = ?")
            params.append(course_name)
        date_start = plan.get("date_start")
        date_end = plan.get("date_end")
        if bool(date_start) != bool(date_end):
            raise SQLCompileError("考试成绩排名日期范围不完整")
        if date_start and date_end:
            try:
                start = date.fromisoformat(str(date_start))
                end = date.fromisoformat(str(date_end))
            except ValueError as exc:
                raise SQLCompileError("考试成绩排名日期范围无效") from exc
            if start >= end:
                raise SQLCompileError("考试成绩排名日期范围顺序无效")
            where.extend(("[k].[clerk_ks_btime] >= ?", "[k].[clerk_ks_btime] < ?"))
            params.extend((start.isoformat(), end.isoformat()))
        where.extend(("[k].[Clerk_ks_status] = ?", "[k].[Cj] IS NOT NULL"))
        params.append(1)
        direction = "ASC" if order == "asc" else "DESC"
        sql += (
            " WHERE " + " AND ".join(where)
            + " GROUP BY [s].[Id], [s].[ActualName]"
            + f" ORDER BY [{alias}] {direction}, [s].[ActualName] ASC, [s].[Id] ASC;"
        )
        if not sql.upper().startswith("SELECT") or ";" in sql[:-1]:
            raise SQLCompileError("编译器只允许生成一条SELECT")
        return sql, params

    def _prepare_joins(
        self, primary_table: str, requested: list[dict[str, Any]]
    ) -> tuple[dict[str, str], str]:
        aliases = {primary_table: "t0"}
        if not requested:
            return aliases, ""
        pending: list[dict[str, Any]] = []
        seen = set()
        for rule in requested:
            try:
                key = join_rule_key(rule)
            except KeyError as exc:
                raise SQLCompileError(f"关联定义不完整: {rule}") from exc
            if key not in self.allowed_joins:
                raise SQLCompileError(f"关联不在白名单中: {rule}")
            if key not in seen:
                pending.append(self.allowed_joins[key])
                seen.add(key)

        fragments: list[str] = []
        while pending:
            progressed = False
            for rule in list(pending):
                left = rule["left_table"]
                right = rule["right_table"]
                if left in aliases and right in aliases:
                    pending.remove(rule)
                    progressed = True
                    continue
                if left in aliases:
                    existing_table, new_table = left, right
                elif right in aliases:
                    existing_table, new_table = right, left
                else:
                    continue
                aliases[new_table] = f"t{len(aliases)}"
                left_column = self._column(
                    rule["left_field"], left, aliases, qualify=True
                )
                right_column = self._column(
                    rule["right_field"], right, aliases, qualify=True
                )
                fragments.append(
                    f" INNER JOIN {quote_identifier(new_table, self.dialect)} "
                    f"AS {quote_identifier(aliases[new_table], self.dialect)} "
                    f"ON {left_column} = {right_column}"
                )
                pending.remove(rule)
                progressed = True
            if not progressed:
                raise SQLCompileError("关联路径没有连接到主表")
        return aliases, "".join(fragments)

    def _column(
        self,
        field_name: str,
        table_name: str,
        aliases: dict[str, str],
        qualify: bool,
    ) -> str:
        column = quote_identifier(field_name, self.dialect)
        if not qualify:
            return column
        if table_name not in aliases:
            raise SQLCompileError(f"字段所属表未连接: {table_name}.{field_name}")
        return f"{quote_identifier(aliases[table_name], self.dialect)}.{column}"

    def _field(self, table_name: str, name: str | None) -> dict[str, Any]:
        if table_name not in self.tables:
            raise SQLCompileError(f"未知字段所属表: {table_name}")
        fields = field_map(self.tables[table_name])
        if not name or name not in fields:
            raise SQLCompileError(f"未知字段: {table_name}.{name}")
        return fields[name]

    @staticmethod
    def _require_joined(table_name: str, aliases: dict[str, str]) -> None:
        if table_name not in aliases:
            raise SQLCompileError(f"查询引用了未连接的表: {table_name}")

    def _aggregate(
        self,
        metric: dict[str, Any] | None,
        aggregation: str,
        metric_table: str,
        aliases: dict[str, str],
        qualified: bool,
    ) -> tuple[str, str]:
        if aggregation == "count":
            return "COUNT_BIG(*)", "record_count"
        if aggregation not in {"sum", "avg", "max", "min"}:
            raise SQLCompileError(f"不支持的聚合方式: {aggregation}")
        if metric is None:
            raise SQLCompileError("缺少聚合字段")
        column = self._column(metric["name"], metric_table, aliases, qualified)
        return f"{aggregation.upper()}({column})", f"{aggregation}_{metric['name']}"

    @staticmethod
    def _list_fields(table: dict[str, Any]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        pk = primary_key(table)
        if pk:
            selected.append(pk)
        priorities = (
            "name",
            "title",
            "actualname",
            "status",
            "type",
            "createtime",
            "createdtime",
            "begintime",
            "endtime",
        )
        by_name = {field["name"].lower(): field for field in table["fields"]}
        for name in priorities:
            if name in by_name and by_name[name] not in selected:
                selected.append(by_name[name])
        for field in table["fields"]:
            if field not in selected and field["type"] not in {"image", "binary", "varbinary"}:
                selected.append(field)
            if len(selected) >= 8:
                break
        return selected or table["fields"][:8]
