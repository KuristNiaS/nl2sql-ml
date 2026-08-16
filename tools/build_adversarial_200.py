from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nl2sql_ml.schema import load_catalog, table_map


ROLES = (
    "考试管理员",
    "教务管理员",
    "任课教师",
    "培训管理员",
    "部门培训负责人",
    "系统管理员",
)


def main() -> None:
    root = ROOT
    catalog = load_catalog()
    tables = table_map(catalog)
    cases: list[dict[str, Any]] = []

    def add(category: str, style: str, question: str, expected: dict[str, Any]) -> None:
        cases.append(
            {
                "id": f"adv-{len(cases) + 1:03d}",
                "role": ROLES[len(cases) % len(ROLES)],
                "category": category,
                "style": style,
                "question": question,
                "expected": expected,
            }
        )

    list_scenarios = (
        ("Student_Info", "学员"),
        ("Course_Info", "课程"),
        ("Study_Class_Info", "学习班"),
        ("Exam_Apply", "考试报名"),
        ("clerk_kscj", "考试成绩"),
        ("News_Info", "新闻资讯"),
        ("BBSReplayInfo", "回帖"),
        ("Sys_Mail_Info", "站内邮件"),
        ("Evaluation", "考评活动"),
        ("Skill_Info", "能力"),
    )
    list_styles = (
        ("简洁指令", "查询{label}记录"),
        ("礼貌请求", "请帮我列出{label}明细"),
        ("后台操作", "后台需要查看{label}列表"),
        ("口语核对", "我想核对一下系统里的{label}记录"),
    )
    for table, label in list_scenarios:
        assert table in tables
        for style, template in list_styles:
            add(
                "明细查询",
                style,
                template.format(label=label),
                {"plan": {"intent": "list", "table": table}, "sql_contains": [f"FROM [{table}]" ]},
            )

    count_scenarios = (
        ("Department", "部门"),
        ("Duty_Info", "岗位"),
        ("tk_tkj", "题库集"),
        ("BBSTopicInfo", "论坛主题"),
        ("Role_Info", "角色"),
        ("Sys_Access_Info", "系统权限"),
        ("GameArrangeInfo", "闯关游戏参加人员安排"),
        ("Skill_Level_Info", "能力等级"),
        ("Certificate_Info", "证书"),
        ("OffTrain_Info", "线下培训"),
    )
    count_styles = (
        ("统计口径", "统计{label}数量"),
        ("自然问法", "后台一共有多少条{label}记录"),
        ("核对总数", "请核对{label}总数"),
    )
    for table, label in count_scenarios:
        assert table in tables
        for style, template in count_styles:
            add(
                "计数查询",
                style,
                template.format(label=label),
                {
                    "plan": {"intent": "count", "table": table, "aggregation": "count"},
                    "sql_contains": ["COUNT_BIG(*)", f"FROM [{table}]"],
                },
            )

    group_scenarios = (
        ("Course_Info", "课程", "状态", "Status"),
        ("Study_Class_Info", "学习班", "状态", "Status"),
        ("Exam_Apply", "考试报名", "状态", "Status"),
        ("News_Info", "新闻资讯", "栏目类型标识", "NewsTypeId"),
        ("User_Option_Info", "企业用户配置", "类型", "Type"),
        ("Evaluation_Result", "评分记录", "状态", "Status"),
        ("GameStudentInfo", "员工游戏情况", "状态", "Status"),
        ("Student_Skill_Info", "员工能力", "评定来源", "SourceType"),
        ("tk001", "题目", "题型ID", "Tm_tx_ID"),
        ("Department", "部门", "部门编号", "DeptNo"),
    )
    group_styles = (
        ("标准分组", "按{dim}统计{label}数量"),
        ("报表需求", "请给我一份{label}按{dim}分组的数量报表"),
        ("口语分组", "各{dim}分别有多少条{label}记录"),
    )
    for table, label, dim_label, dim_field in group_scenarios:
        assert any(field["name"] == dim_field for field in tables[table]["fields"]), (table, dim_field)
        for style, template in group_styles:
            add(
                "分组计数",
                style,
                template.format(label=label, dim=dim_label),
                {
                    "plan": {
                        "intent": "group_aggregate",
                        "table": table,
                        "dimension_column": dim_field,
                        "aggregation": "count",
                    },
                    "sql_contains": ["COUNT_BIG(*)", f"GROUP BY [{dim_field}]"],
                },
            )

    top_scenarios = (
        ("课程学分最高的前5个课程名称", "Course_Info", "CreditHour", "Name", "sum", 5),
        ("按课时找出排名前10的课程名称", "Course_Info", "Hour", "Name", "sum", 10),
        ("课程星级最高的前3个课程名称", "Course_Info", "StarLevel", "Name", "sum", 3),
        ("累计积分最高的前10名学员真实姓名", "Student_Info", "PointsTotal", "ActualName", "sum", 10),
        ("当前积分余额最高的前5名学员真实姓名", "Student_Info", "PointsBalance", "ActualName", "sum", 5),
        ("热度排名前10的课程名称", "Course_Info", "Hots", "Name", "sum", 10),
        ("学分最低的前5个课程名称", "Course_Info", "CreditHour", "Name", "sum", 5),
        ("积分最高的前3个课程名称", "Course_Info", "Integral", "Name", "sum", 3),
    )
    for question, table, metric, dimension, aggregation, limit in top_scenarios:
        for style, prefix in (("简洁排名", "查询"), ("管理报表", "后台报表：")):
            order = "asc" if "最低" in question else "desc"
            add(
                "Top N",
                style,
                prefix + question,
                {
                    "plan": {
                        "intent": "top_n",
                        "table": table,
                        "metric_column": metric,
                        "dimension_column": dimension,
                        "aggregation": aggregation,
                        "limit": limit,
                        "order": order,
                    },
                    "sql_contains": [f"SELECT TOP ({limit})", f"{aggregation.upper()}([{metric}])", f"GROUP BY [{dimension}]"],
                },
            )

    time_scenarios = (
        ("Exam_Apply", "考试报名", "CreateTime"),
        ("Course_Info", "创建的课程", "CreatedTime"),
        ("Study_Class_Info", "创建的学习班", "CreatedTime"),
        ("clerk_kscj", "考试成绩", "clerk_ks_btime"),
        ("News_Info", "创建的新闻资讯", "CreatedTime"),
        ("Duty_Info", "创建的岗位", "CreateTime"),
        ("Evaluation", "创建的考评活动", "CreateTime"),
        ("Skill_Info", "创建的能力", "CreateTime"),
    )
    for index, (table, label, time_field) in enumerate(time_scenarios):
        year = 2021 + index
        for style, template in (
            ("年度查询", "查询{year}年度{label}记录"),
            ("教师口语", "帮我调出{year}年全部{label}"),
        ):
            add(
                "年度筛选",
                style,
                template.format(year=year, label=label),
                {
                    "plan": {"intent": "list", "table": table, "time_field": time_field},
                    "params": [f"{year}-01-01", f"{year + 1}-01-01"],
                    "sql_contains": [f"[{time_field}] >= ?", f"[{time_field}] < ?"],
                },
            )

    join_scenarios = (
        ("查询张三所有的考试报名记录", "请把张三的全部考试报名明细调出来", "Exam_Apply", ["张三"], "[ActualName] = ?"),
        ("查询李四的考试成绩", "我想查看李四参加考试后的成绩记录", "clerk_kscj", ["李四"], "[ActualName] = ?"),
        ("查询参加年度培训课程的学员名单", "列出选修年度培训这门课程的学员", "Student_Info", ["年度培训"], "[Name] = ?"),
        ("查询张三参加的学习班", "张三都参加过哪些学习班，给我列表", "Study_Class_Info", ["张三"], "[ActualName] = ?"),
        ("查询姓名为王五的员工能力记录", "调出王五对应的员工能力明细", "Student_Skill_Info", ["王五"], "[ActualName] = ?"),
        ("查询课程名称为安全生产的学员学习课程日志", "查看安全生产课程对应的学习日志", "Student_Course_Log", ["安全生产"], "[Name] = ?"),
        ("查询用户名为zhangsan的积分日志", "把账号zhangsan的积分变动记录找出来", "Student_Point_Log", ["zhangsan"], "[Name] = ?"),
        ("查询学员姓名为陈晨的学员课件学习记录", "陈晨的课件学习记录有哪些", "Student_Courseware_Info", ["陈晨"], "[ActualName] = ?"),
        ("查询学习班名称为管理提升班的学习班报名申请记录", "查看管理提升班收到的报名申请", "Study_Class_Apply_Info", ["管理提升班"], "[Name] = ?"),
        ("查询能力名称为数据分析的员工能力记录", "哪些员工能力记录对应数据分析能力", "Student_Skill_Info", ["数据分析"], "[Name] = ?"),
    )
    for standard, colloquial, table, params, filter_sql in join_scenarios:
        for style, question in (("标准实体筛选", standard), ("业务口语", colloquial)):
            add(
                "跨表实体",
                style,
                question,
                {
                    "plan": {"table": table},
                    "params": params,
                    "min_joins": 1,
                    "sql_contains": ["INNER JOIN", filter_sql],
                },
            )

    kpi_questions = (
        "2026年度各部门一至十二月份人均学习时长横向对比",
        "2025年不同部门每个月平均每人培训学时趋势报表",
        "各部门2024全年逐月员工人均课程学习时间对比表",
        "2023年度按部门月度每人平均学习用时汇总",
        "教务后台要看2022年各部门每月人均学习小时数",
        "请导出2021全年部门维度的一到十二月人均培训时长",
        "做一张2020年各部门逐月人均课程学习时长横表",
        "老师需要2019年度部门月度平均每人学习时间对照表",
    )
    for question in kpi_questions:
        add(
            "审核KPI",
            "报表表达",
            question,
            {
                "plan": {"report_type": "department_monthly_per_capita_learning_hours", "intent": "cross_tab"},
                "sql_contains": ["LEFT JOIN [Student_Course_Log]", "[1月人均学习时长_小时]", "[12月人均学习时长_小时]"],
            },
        )

    score_aggregate_cases = (
        ("2026年张三和李四各自在线性代数中取得的最高分", "max", ["张三", "李四"], "线性代数", 2026),
        ("查询2025年度王五与赵敏分别在高等数学课程中的最低成绩", "min", ["王五", "赵敏"], "高等数学", 2025),
        ("统计张三、李四以及王五各人2024全年在课程名称为数据分析的考试中的平均分", "avg", ["张三", "李四", "王五"], "数据分析", 2024),
        ("2023年刘洋跟陈晨各自在安全生产中获得的最高成绩", "max", ["刘洋", "陈晨"], "安全生产", 2023),
        ("请查看2022年度周静及孙强分别在职业道德里的平均得分", "avg", ["周静", "孙强"], "职业道德", 2022),
        ("李四和杨帆每人2021年在质量管理中考出的最低分", "min", ["李四", "杨帆"], "质量管理", 2021),
        ("2020年赵敏与王五各人在线性代数拿到的平均成绩", "avg", ["赵敏", "王五"], "线性代数", 2020),
        ("帮我查2019年度张三、刘洋分别在高等数学取得的最高得分", "max", ["张三", "刘洋"], "高等数学", 2019),
        ("2026年张三和李四各自最高分", "max", ["张三", "李四"], None, 2026),
        ("王五与赵敏分别取得的最低成绩", "min", ["王五", "赵敏"], None, None),
        ("陈晨和周静各人今年考试平均分", "avg", ["陈晨", "周静"], None, 2026),
        ("去年孙强及杨帆每人的最高成绩", "max", ["孙强", "杨帆"], None, 2025),
        ("张三在线性代数中的最高分", "max", ["张三"], "线性代数", None),
        ("查询李四在高等数学里的最低成绩", "min", ["李四"], "高等数学", None),
        ("赵敏的数据分析平均得分", "avg", ["赵敏"], "数据分析", None),
        ("请查看王五2024年安全生产课程中的最高成绩", "max", ["王五"], "安全生产", 2024),
    )
    for question, aggregation, people, course, year in score_aggregate_cases:
        ast = {
            "measure.aggregation": aggregation,
            "filters.student_name.values": people,
            "filters.course_name": course,
            "filters.calendar_year": year,
        }
        add(
            "个人成绩组合",
            "交叉表达",
            question,
            {
                "plan": {"report_type": "student_exam_score_aggregate", "aggregation": aggregation},
                "ast": ast,
                "sql_contains": [f"{aggregation.upper()}([k].[Cj])", "GROUP BY [s].[Id], [s].[ActualName]"],
            },
        )

    score_ranking_cases = (
        ("2026年所有课程平均成绩最高的10个学生", "avg", 10, "desc", None, None, "all_courses", 2026),
        ("2026年研发部所有课程平均成绩最高的10个学生", "avg", 10, "desc", "研发部", None, "all_courses", 2026),
        ("2025年度高等数学平均分最低的5名学员", "avg", 5, "asc", None, "高等数学", "specific", 2025),
        ("2024年线性代数平均成绩排名前20的学生", "avg", 20, "desc", None, "线性代数", "specific", 2024),
        ("数据分析课程平均得分最高的前3名学员", "avg", 3, "desc", None, "数据分析", "specific", None),
        ("安全生产课程最高分排名前10的考生", "max", 10, "desc", None, "安全生产", "specific", None),
        ("职业道德最低成绩倒数5名学生", "min", 5, "asc", None, "职业道德", "specific", None),
        ("2023年全部考试平均成绩排行榜前10名学员", "avg", 10, "desc", None, None, "all_exams", 2023),
        ("部门为培训部的学生2022年所有课程平均分前5名", "avg", 5, "desc", "培训部", None, "all_courses", 2022),
        ("筛选生产部2021年全部课程平均成绩最高的20个学员", "avg", 20, "desc", "生产部", None, "all_courses", 2021),
        ("教务处所有课程平均成绩最低的前10名学生", "avg", 10, "asc", "教务处", None, "all_courses", None),
        ("考试中心全部课程平均分排行前五名考生", "avg", 5, "desc", "考试中心", None, "all_courses", None),
        ("2020年度质量管理平均得分Top10学生", "avg", 10, "desc", None, "质量管理", "specific", 2020),
        ("2019年高等数学最高成绩最好的3名学员", "max", 3, "desc", None, "高等数学", "specific", 2019),
        ("线性代数最低分最低的前5个考生", "min", 5, "asc", None, "线性代数", "specific", None),
        ("所有考试平均成绩排名前10的人员", "avg", 10, "desc", None, None, "all_exams", None),
    )
    for question, aggregation, limit, order, department, course, scope, year in score_ranking_cases:
        add(
            "成绩排名组合",
            "排名表达",
            question,
            {
                "plan": {
                    "report_type": "student_exam_score_ranking",
                    "aggregation": aggregation,
                    "limit": limit,
                    "order": order,
                },
                "ast": {
                    "filters.department": department,
                    "filters.course_name": course,
                    "filters.course_scope": scope,
                    "filters.calendar_year": year,
                },
                "sql_contains": [f"SELECT TOP ({limit})", f"{aggregation.upper()}([k].[Cj])", "GROUP BY [s].[Id], [s].[ActualName]"],
            },
        )

    reject_cases = (
        ("2026年数学专业所有课程平均成绩最高的10个学生", "Student_Info学员表没有专业字段"),
        ("2026年度各部门每月学习时长中位数对比", "已审核的KPI规则"),
        ("2026年张三和李四在线性代数中的最高分", "分别统计还是合并统计"),
        ("查询张三创建的课程", "没有安全、明确的关联路径"),
        ("查询量子涨落熵系数", "目标事实表无法可靠识别"),
        ("2026年一年级所有课程平均成绩前10名学生", "没有年级字段"),
        ("2026年软件学院全部课程平均分最高的5个学员", "没有学院字段"),
        ("2026年三班所有课程平均成绩排名前10的学生", "没有班级字段"),
    )
    for question, error in reject_cases:
        add("安全拒绝", "缺失口径", question, {"error_contains": error})

    ambiguous_courseware = next(
        case for case in cases if case["question"] == "陈晨的课件学习记录有哪些"
    )
    ambiguous_courseware["category"] = "安全拒绝"
    ambiguous_courseware["style"] = "粒度歧义"
    ambiguous_courseware["expected"] = {"error_contains": "课件学习记录”在设计书中存在两种口径"}

    if len(cases) != 200:
        raise AssertionError(f"对抗测试数量必须是200，实际为{len(cases)}")
    questions = [case["question"] for case in cases]
    if len(set(questions)) != 200:
        raise AssertionError("对抗测试问句必须全部唯一")

    output = root / "data" / "adversarial_200.jsonl"
    output.write_text(
        "\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n",
        encoding="utf-8",
    )
    summary = {
        "cases": len(cases),
        "roles": sorted({case["role"] for case in cases}),
        "categories": {category: sum(case["category"] == category for case in cases) for category in sorted({case["category"] for case in cases})},
        "styles": len({case["style"] for case in cases}),
        "output": str(output),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
