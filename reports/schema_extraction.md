# 数据库设计书提取报告

- 文档页数：53
- Word表格对象：114
- 唯一业务表：111
- 提取字段：1088
- 推断关系：48
- 查询白名单关系：89
- 类型未知字段：68
- 未明确主键表：0

## 业务域覆盖

| 业务域 | 表数 |
| --- | ---: |
| 帐户系列 | 7 |
| 题库系列 | 5 |
| 考试系列 | 18 |
| 培训系列 | 31 |
| 论坛系列 | 3 |
| 参数配置 | 1 |
| 消息通知 | 3 |
| 系统数据 | 19 |
| 资讯中心 | 3 |
| 评分活动 | 10 |
| 闯关游戏 | 4 |
| 员工培训技能矩阵 | 7 |

## 提取限制

- 评分活动部分表格没有类型列，对应字段保留为 `UNKNOWN`。
- 外键关系来自文档中的 FK 标记、字段名和说明推断，必须在连接真实数据库前核验。
- 参数配置的两张 OptionName/OptionValue 表被识别为配置字典续表，不计为独立业务表。
- 重复出现的同名表已合并，并保留 `duplicate_source_indices`。
- 设计书把 `tk_lx` 标题写成“题库集表”，而字段说明定义为节（题库）；目录保留原始标题，查询词典使用“题库/节题库”消除歧义。
- `Certificate_Info` 中 `ImageUrl`/`CreateTime` 等类型按设计书原样保留，不基于字段名擅自改型。
- 所有表的 `SerialNo` 按设计书全局修改统一为 `bigint NOT NULL IDENTITY`，原始类型保存在 `source_type`。

## 未明确主键的表

无

## 类型未知字段

WebFile_Image.Other2, Lectuer_Info.Type, Sys_Access_Info.UseRange, Evaluation_Group.Id, Evaluation_Group.Title, Evaluation_Group.UserId, Evaluation_Group.CreateTime, Evaluation_Group.CreatorId, Evaluation.Id, Evaluation.Title, Evaluation.Subject, Evaluation.LimitedTime, Evaluation.BeginTime, Evaluation.EndTime, Evaluation.UserId, Evaluation.CreateTime, Evaluation.CreatorId, Evaluation_Items.Id, Evaluation_Items.EvaluationId, Evaluation_Items.Item, Evaluation_Items.CreateTime, Evaluation_Items.OrderNumber, Evaluation_Score_Item.Id, Evaluation_Score_Item.EvaluationItemId, Evaluation_Score_Item.Item, Evaluation_Score_Item.ItemType, Evaluation_Score_Item.ItemSubject, Evaluation_Score_Item.Score, Evaluation_Score_Item.CreateTime, Evaluation_Score_Item.OrderNumber, Evaluation_Score_Item_Detail.Id, Evaluation_Score_Item_Detail.EvaluationScoreItemId, Evaluation_Score_Item_Detail.Item, Evaluation_Score_Item_Detail.Score, Evaluation_Score_Item_Detail.CreateTime, Evaluation_Score_Item_Detail.OrderNumber, Evaluation_Expert.Id, Evaluation_Expert.EvaluationId, Evaluation_Expert.ExpertId, Evaluation_Expert.CreateTime, Evaluation_Person.Id, Evaluation_Person.EvaluationId, Evaluation_Person.PersonId, Evaluation_Person.CreateTime, Evaluation_Result.Id, Evaluation_Result.EvaluationId, Evaluation_Result.PersonId, Evaluation_Result.ExpertId, Evaluation_Result.BeginTime, Evaluation_Result.EndTime, Evaluation_Result.TimeOut, Evaluation_Result.DockPoints, Evaluation_Result.Remark, Evaluation_Result.TotalScore, Evaluation_Result.CreateTime, Evaluation_Result.LimitedTime, Evaluation_Result.Status, Evaluation_Result_Item.Id, Evaluation_Result_Item.ResultId, Evaluation_Result_Item.ItemId, Evaluation_Result_Item.Score, Evaluation_Result_Item.Remark, Evaluation_Result_Item.CreateTime, Evaluation_Result_Item_Detail.Id, Evaluation_Result_Item_Detail.ResultItemId, Evaluation_Result_Item_Detail.CreateTime, Evaluation_Result_Item_Detail.DetailId, Evaluation_Result_Item_Detail.ResultId