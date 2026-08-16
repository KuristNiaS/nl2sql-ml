from __future__ import annotations

import json
from pathlib import Path


def generate_model_report(
    catalog_path: str | Path,
    dataset_summary_path: str | Path,
    evaluation_path: str | Path,
    acceptance_path: str | Path,
    output_path: str | Path,
) -> None:
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    dataset = json.loads(Path(dataset_summary_path).read_text(encoding="utf-8"))
    evaluation = json.loads(Path(evaluation_path).read_text(encoding="utf-8"))
    acceptance = json.loads(Path(acceptance_path).read_text(encoding="utf-8"))
    adversarial_path = Path(dataset_summary_path).parent / "adversarial_200_report.json"
    adversarial = (
        json.loads(adversarial_path.read_text(encoding="utf-8"))
        if adversarial_path.exists()
        else None
    )
    complexity = dataset.get("complexity", {})
    lines = [
        "# 培训系统 NL2SQL 模型报告",
        "",
        "## 结论",
        "",
        f"系统覆盖设计书中的 **{catalog['extraction']['unique_tables']} 张业务表**、"
        f"**{catalog['extraction']['fields']} 个字段**和 **{len(catalog['domains'])} 个业务域**，"
        "SQL 目标方言为 Microsoft SQL Server。",
        "",
        "系统使用字符 TF-IDF + 线性 SVM 识别有限标签；实体、日期、字段和受控联表由确定性语义层处理；"
        "SQL 由白名单编译器生成。下列准确率来自合成数据和独立人工验收问句，不能替代真实只读数据库上的执行正确率。",
        "",
        "## Schema 与安全关联",
        "",
        f"- 设计书候选关系：{len(catalog.get('relations', []))}",
        f"- 可用于生成 SQL 的审核关联：{len(catalog.get('query_joins', []))}",
        "- 普通关联类型：仅白名单 `INNER JOIN`；审核 KPI 模板可使用固定 `LEFT JOIN` 以保留零学习人员",
        "- 筛选值：全部使用 `?` 参数，不拼接到 SQL",
        "",
        "## 数据集",
        "",
        f"- 样本数：{dataset['samples']:,}",
        f"- 唯一问句：{dataset.get('unique_questions', dataset['samples']):,}",
        f"- 全表基础样本：{dataset.get('base_samples', dataset['samples']):,}",
        f"- 复杂语义专项样本：{dataset.get('specialized_report_samples', 0):,}",
        f"  - 部门逐月人均学习时长：{dataset.get('monthly_report_samples', 0):,}",
        f"  - 学员考试成绩组合查询：{dataset.get('compositional_exam_score_samples', 0):,}",
        f"  - 学员考试成绩排名查询：{dataset.get('exam_score_ranking_samples', 0):,}",
        f"- 表覆盖：{dataset['tables_covered']}/{catalog['extraction']['unique_tables']}",
        f"- 基础样本每表范围：{dataset.get('base_table_min_samples', dataset['table_min_samples'])}–{dataset.get('base_table_max_samples', dataset['table_max_samples'])}",
        f"- 联表查询：{complexity.get('joined_queries', 0):,}",
        f"- 多条件查询：{complexity.get('multi_filter_queries', 0):,}",
        f"- 时间筛选查询：{complexity.get('time_filter_queries', 0):,}",
        f"- 跨表分组维度查询：{complexity.get('remote_dimension_queries', 0):,}",
        f"- 年度×部门×月份人均学习时长横表：{complexity.get('cross_tab_queries', 0):,}",
        f"- 年度×多人×课程×成绩聚合查询：{complexity.get('compositional_exam_score_queries', 0):,}",
        f"- 年度×组织/课程范围×学生成绩排名：{complexity.get('exam_score_ranking_queries', 0):,}",
        "",
        "## 合成留出集分类结果",
        "",
        "| 任务 | 准确率 | 类别数 | 测试样本 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for target, metrics in evaluation["targets"].items():
        lines.append(
            f"| {target} | {metrics['accuracy']:.2%} | {len(metrics['classes'])} | {metrics['test_samples']} |"
        )
    lines.extend(
        [
            "",
            "## 独立验收集",
            "",
            f"- 通过：{acceptance['passed']}/{acceptance['cases']}",
            f"- 用例准确率：{acceptance['case_accuracy']:.2%}",
            f"- 字段级准确率：{acceptance['field_accuracy']:.2%}",
            f"- 数据集 Schema 覆盖率：{acceptance['schema_coverage']['coverage']:.2%}",
            *(
                [f"- 后台人员/教师风格对抗测试：{adversarial.get('passed_in_this_run', 0)}/200"]
                if adversarial and adversarial.get("status") == "passed" and adversarial.get("range") == [1, 200]
                else []
            ),
            "",
            "复杂验收覆盖姓名/用户名/部门/课程/学习班/线下培训/能力等实体筛选、"
            "一至四跳联表、跨表分组、Top N、多条件与日期组合；同时覆盖年度×部门×月份的人均学习时长横表，"
            "以及年度×多人×课程×最高/最低/平均考试成绩的组合语义 AST。"
            "学生成绩排名支持自然年、部门、指定课程/所有课程/所有考试、Top N 和升降序。"
            "未知角色或未审核的高级指标会明确拒绝，不能静默忽略条件或退化成计数。",
            "",
            "## 已知限制",
            "",
            "- 合成模板与真实用户表达的分布不同；接近 100% 的合成留出集分数不代表生产准确率。",
            "- 设计书没有真实数据分布，筛选值使用合成占位值。",
            "- 评分活动部分有 68 个字段缺少类型，目录保留为 `UNKNOWN`。",
            "- 关联来自设计书 FK 标记、字段名和说明推断；接入生产库前必须核验连接基数与业务口径。",
            "- 人均学习时长当前以启用学员为分母、课程学习日志有效起止时间为分子；设计书缺少部门/在职历史，因此历史记录按当前部门归属。",
            "- 跨月学习会话按开始月份归属；若生产口径不同，应修改审核 KPI 规则并补充验收。",
            "- 考试成绩按 `clerk_kscj.Cj` 统计且只包含 `Clerk_ks_status=1`；课程关联按设计书解释使用 `tk_cl.SiteID`，并限制 `SiteType IN (1,3)`。",
            "- `tk_cl.SiteID` 为 `int`、`Course_Info.Id` 为 `varchar(50)`，当前使用显式类型转换关联；接入真实库前必须核验该设计书口径和索引性能。",
            "- `Student_Info` 没有专业、年级、学院、班级字段；相关筛选会明确拒绝，不能静默省略。",
            "- 设计书同时存在学员课件汇总记录和课件学习会话；用户只说“课件学习记录”时必须澄清粒度。",
            "- 只允许审核白名单内的安全路径，不自动猜测任意多表关系、子查询、窗口函数或写操作。",
            "- 真实上线应以 SQL 执行正确率和结果集正确率为主指标。",
            "",
            "## 主要产物",
            "",
            "- `config/schema_catalog.json`：Schema、关系与查询联表白名单",
            "- `config/semantic_layer.json`：审核事实、指标、维度、关联和口径假设",
            "- `config/business_dictionary.json`：表/字段别名、实体、操作符与时间词典",
            "- `data/dataset.jsonl`：训练数据、计划、目标 SQL 与参数",
            "- `data/acceptance.jsonl`：独立人工验收语句",
            "- `data/adversarial_200.jsonl`：200 条后台人员/教师多风格对抗问句",
            "- `artifacts/model.joblib`：传统机器学习模型",
            "- `artifacts/evaluation.json`：分类评估",
            "- `artifacts/acceptance_report.json`：端到端验收",
            "- `artifacts/adversarial_200_report.json`：200 条顺序 Shell 测试明细",
            "- `artifacts/learning_curves.png`：离线学习曲线",
        ]
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8-sig")


def generate_acceptance_report(
    cases_path: str | Path,
    result_path: str | Path,
    output_path: str | Path,
) -> None:
    cases = [
        json.loads(line)
        for line in Path(cases_path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    details = result.get("details", [])
    lines = [
        "# NL2SQL 人工验收报告",
        "",
        f"- 用例：{result['cases']}",
        f"- 通过：{result['passed']}",
        f"- 用例准确率：{result['case_accuracy']:.2%}",
        f"- 字段级准确率：{result['field_accuracy']:.2%}",
        f"- Schema 覆盖率：{result['schema_coverage']['coverage']:.2%}",
        "",
        "验收集独立于训练数据，由人工按设计书业务域编写；仍需在真实只读数据库补充 SQL 执行与结果集正确率验证。",
    ]
    current_domain = None
    for case, detail in zip(cases, details):
        domain = case.get("domain", "unknown")
        if domain != current_domain:
            lines.extend(["", f"## {domain}"])
            current_domain = domain
        status = "通过" if detail.get("passed") else "失败"
        lines.extend(
            [
                "",
                f"### {case.get('id', '')} · {status}",
                "",
                f"- 问句：{case['question']}",
                f"- 期望：`{json.dumps(case['expected'], ensure_ascii=False)}`",
                f"- 差异：`{json.dumps(detail.get('mismatches', {}), ensure_ascii=False)}`",
                "",
                "```sql",
                detail.get("sql") or "-- 未生成 SQL",
                "```",
            ]
        )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8-sig")
