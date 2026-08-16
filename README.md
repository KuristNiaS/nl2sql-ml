# 培训系统轻量级中文 NL2SQL

本项目根据《数据库设计文档》重构，不使用大语言模型。系统用字符 TF-IDF + 线性 SVM 识别有限分类标签，用可审计的语义层把事实、指标、维度和筛选组合成 AST，最后通过白名单编译器生成参数化的 Microsoft SQL Server `SELECT`。SVM 不直接生成 SQL。

当前版本包含：

- 12 个业务域、111 张业务表、1088 个有效字段；
- 48 条设计书候选关系、89 条可用于查询的审核关联白名单；
- 72,000 条互不重复的合成训练数据：60,000 条全表基础样本、4,000 条复合 KPI、4,000 条个人考试成绩组合和 4,000 条学生成绩排名改写；
- 82 条人工编写的跨业务域验收语句，以及 200 条后台管理人员/教师多风格对抗问句；
- 已训练模型、分类报告、验收报告、学习曲线和单元测试；
- 纯命令行使用，不启动网页，也不需要 `localhost`。

## 安装

项目使用现有 Conda 环境 `SCUPI`。在 Windows CMD 中执行：

```bat
cd /d E:\nl2sql-ml
conda run --no-capture-output -n SCUPI python -m pip install -e .
```

安装后可在任意目录运行。若只想使用已经生成的模型，运行时主要依赖 scikit-learn、SciPy、NumPy、pandas 和 joblib，不需要 GPU。

## 直接测试翻译

```bat
conda run --no-capture-output -n SCUPI python -m nl2sql_ml schema

conda run --no-capture-output -n SCUPI python -m nl2sql_ml ask "查询本月创建的岗位" --pretty

conda run --no-capture-output -n SCUPI python -m nl2sql_ml ask "查询张三所有的考试报名记录" --pretty

conda run --no-capture-output -n SCUPI python -m nl2sql_ml ask "按状态统计学习班数量" --pretty

conda run --no-capture-output -n SCUPI python -m nl2sql_ml ask "查询课程学分最高的前5个课程名称" --pretty

conda run --no-capture-output -n SCUPI python -m nl2sql_ml ask "2026年度各部门一至十二月份人均学习时长横向对比" --pretty

conda run --no-capture-output -n SCUPI python -m nl2sql_ml ask "2026年张三和李四各自在线性代数中取得的最高分" --pretty

conda run --no-capture-output -n SCUPI python -m nl2sql_ml ask "2026年所有课程平均成绩最高的10个学生" --pretty
```

`ask` 只生成 SQL 和参数，不会连接或修改数据库。输出示例：

```json
{
  "sql": "SELECT [Status] AS [Status], COUNT_BIG(*) AS [record_count] FROM [Study_Class_Info] GROUP BY [Status];",
  "params": [],
  "plan": {
    "intent": "group_aggregate",
    "table": "Study_Class_Info",
    "dimension_column": "Status",
    "aggregation": "count"
  }
}
```

筛选值不会被拼进 SQL。例如“查询张三所有的考试报名记录”会通过 `Exam_Apply.StudentId = Student_Info.Id` 的白名单关联生成 `INNER JOIN`，条件为 `[t1].[ActualName] = ?`，并把 `张三` 单独放入 `params`。接入 pyodbc 等驱动时，将 SQL 与参数数组一起提交即可。

## 验收和测试

```bat
cd /d E:\nl2sql-ml
conda run --no-capture-output -n SCUPI python -m nl2sql_ml evaluate
conda run --no-capture-output -n SCUPI python -m unittest discover -s tests -v
conda run --no-capture-output -n SCUPI python tools\run_adversarial_200.py
```

当前已保存的结果：

- 分类测试集：意图、业务域、物理表、聚合方式均为 100%；
- 人工验收集：82/82 通过；
- 后台人员/教师多风格对抗集：200/200 通过；
- Schema 数据集覆盖率：111/111 张表，基础样本每表 540–541 条；
- 复杂度：23,363 条联表、18,706 条多条件、34,360 条时间筛选、15,000 条跨表分组样本；
- 专项组合：4,000 条年度×部门×月份人均学习时长、4,000 条个人成绩聚合、4,000 条学生成绩排名；
- 组合语义回放：8,000/8,000 条 AST 精确一致；
- 自动测试：27/27 通过。

这些数字衡量的是合成数据及当前人工验收集，不能等同于真实数据库上的执行正确率。上线前应补充真实用户问句，并使用只读测试库核验查询结果。

## 重新生成与训练

完整构建：

```bat
conda run --no-capture-output -n SCUPI python -m nl2sql_ml build --samples 72000
```

如果只改了某一步，也可以分别运行：

```bat
conda run --no-capture-output -n SCUPI python -m nl2sql_ml generate --samples 72000
conda run --no-capture-output -n SCUPI python -m nl2sql_ml train
conda run --no-capture-output -n SCUPI python -m nl2sql_ml plots
```

`plots` 直接写出 `artifacts/learning_curves.png` 和 CSV，不需要网页。线性 SVM 没有神经网络的 epoch/loss 曲线，因此这里从完整 72,000 条数据中固定抽取最多 12,000 条，绘制“训练样本量—训练/交叉验证准确率”，控制本地 CPU 开销。

## 系统是否必须知道表结构

必须。当前表结构已经从设计书转换为 `config/schema_catalog.json`，字段和表的中文表达位于 `config/business_dictionary.json`，审核指标口径位于 `config/semantic_layer.json`。模型只负责在已知候选项中分类，SQL 编译器只允许使用目录和语义层中的标识符、关系与操作符，因此不会凭空编造数据库结构。

表结构变化后的处理规则：

| 变化 | 是否重新训练 |
| --- | --- |
| 只增加或修改数据库中的数据行 | 不需要 |
| 只修正筛选值、中文同义词 | 通常不需要；修改词典即可，但建议重新跑验收 |
| 新增/删除/重命名表或字段，修改字段类型 | 需要重新提取 Schema、生成数据并训练 |
| 改变事实表、关联或业务口径 | 修改语义层并重新训练，以更新指纹和验收结果 |
| 希望支持新的普通问法 | 补充词典/真实问句；按改动范围决定是否重新生成训练 |

模型文件同时保存 Schema 和语义层指纹。如果表、字段或审核业务口径发生变化，旧模型会被明确拒绝并提示重新训练，避免静默生成过期 SQL。

## 文件说明

| 路径 | 内容 |
| --- | --- |
| `source/数据库设计文档_原始副本.doc` | 用户提供的设计书副本 |
| `source/数据库设计文档.docx` | 用于稳定解析的转换副本 |
| `tools/extract_design_doc.py` | 从设计书重建设计目录和词典 |
| `config/schema_catalog.json` | 完整 Schema、业务域、字段、候选关系与查询关联白名单 |
| `config/business_dictionary.json` | 表/字段别名、实体、操作符和时间表达词典 |
| `config/semantic_layer.json` | 审核事实、指标、维度、关联、固定筛选和口径假设 |
| `data/dataset.jsonl` | 72,000 条唯一训练问句、语义 AST、目标 SQL 与参数 |
| `data/acceptance.jsonl` | 82 条独立人工验收语句 |
| `data/adversarial_200.jsonl` | 200 条后台人员/教师多风格对抗问句与预期 |
| `artifacts/model.joblib` | 已训练的传统机器学习模型 |
| `artifacts/evaluation.json` | 分类测试集报告 |
| `artifacts/acceptance_report.json` | 端到端验收明细 |
| `artifacts/adversarial_200_report.json` | 顺序执行的 200 条对抗测试明细 |
| `reports/acceptance_report.md` | 人工验收语句与逐条生成 SQL |
| `reports/schema_extraction.md` | 设计书提取质量与限制 |
| `reports/model_report.md` | 模型、数据集和验收总结 |

## 当前边界

- 支持明细、计数、聚合、分组、Top N、日期/等值/IN/多条件筛选，以及受控实体关联和跨表分组。
- 支持审核 KPI“年度×部门×1–12月人均学习时长横向对比”，输出十二个月列。当前口径为启用学员数作分母、课程学习日志有效起止时长作分子，单位小时。
- 支持“年度×多名学员×课程×最高/最低/平均考试成绩”的组合语义。成绩来自 `clerk_kscj.Cj`，只统计完成考试；姓名用参数化 `IN`，并按学员 ID 分组，避免同名人员被合并。
- 支持“年度×部门×指定课程/所有课程/所有考试×学生成绩 Top N”。排名按学员 ID 和姓名分组，分值相同时再按姓名、ID 稳定排序。
- 课程成绩关联按设计书解释为 `clerk_kscj.Tk_cl_id → tk_cl.Tk_cl_id`、`tk_cl.SiteID → Course_Info.Id`，且限定 `SiteType IN (1,3)`。由于两侧类型不同，当前 SQL 有显式转换，接真实库前必须核验口径和性能。
- 只使用审核白名单中的 `INNER JOIN` 路径；不会自动猜测任意跨表关系。创建人、审核人等角色不明确时会拒绝生成，避免静默漏掉筛选条件。
- 多人查询未说明“各自/分别/每人”时会要求澄清；无法可靠定位事实表时会拒绝生成，不再输出低置信度的无关计数 SQL。
- 设计书的 `Student_Info` 没有专业、年级、学院、班级字段，所以这些学生筛选会明确拒绝。原问句“数学专业……”必须先确认真实存储字段；不能把讲师表的专业字段误用于学生。
- “课件学习记录”在设计书中有汇总记录和学习会话两种粒度，未说明时会要求澄清。
- 未匹配审核规则的同比、环比、中位数、人均、占比、交叉表等高级需求会明确拒绝，不会退化成普通计数。
- 当前不支持任意子查询、窗口函数、自由组合的报表口径或写操作。

## 为什么暂时不换神经网络

这类错误的核心不是分词或分类能力，而是“人均学习时长”的业务口径和二维输出结构没有定义。神经网络可以帮助识别更多表达，但不能可靠决定分母是全部学员、启用学员还是当月在职人员，也不能凭空知道应使用课程日志还是课件日志。当前方案先用审核 KPI 规则保证 SQL 口径正确；积累足够真实问句后，可以再用小型中文编码器替换 SVM 的分类部分，编译器和 KPI 规则仍应保留。
- 设计书“评分活动”部分缺少字段类型，68 个字段保留为 `UNKNOWN`，不会被自动当作数值指标。
- 设计书本身存在少量类型或标题异常，提取器会保留原始事实，并在提取报告中说明修正规则。

详细原理和扩展方法见 `docs/DESIGN.md`。
