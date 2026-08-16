# NL2SQL 人工验收报告

- 用例：82
- 通过：82
- 用例准确率：100.00%
- 字段级准确率：100.00%
- Schema 覆盖率：100.00%

验收集独立于训练数据，由人工按设计书业务域编写；仍需在真实只读数据库补充 SQL 执行与结果集正确率验证。

## account

### account-01 · 通过

- 问句：查询学员记录
- 期望：`{"table": "Student_Info", "intent": "list", "aggregation": null}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Name], [ActualName], [Status], [CreatedTime], [UserId], [Password], [Degree] FROM [Student_Info];
```

### account-02 · 通过

- 问句：统计部门数量
- 期望：`{"table": "Department", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [Department];
```

### account-03 · 通过

- 问句：查询本月创建的岗位
- 期望：`{"table": "Duty_Info", "intent": "list", "time_field": "CreateTime"}`
- 差异：`{}`

```sql
SELECT TOP (100) [ID], [Name], [CreateTime], [DuteCategoryId], [SerialNo], [Note], [NextDutyId] FROM [Duty_Info] WHERE [CreateTime] >= ? AND [CreateTime] < ?;
```

## question_bank

### question-01 · 通过

- 问句：查询题型明细
- 期望：`{"table": "tm_tx", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Tm_tx_ID], [Tm_tx_name], [BaseType], [DefaultScore], [Notes], [SerialNo] FROM [tm_tx];
```

### question-02 · 通过

- 问句：统计题库集数量
- 期望：`{"table": "tk_tkj", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [tk_tkj];
```

### question-03 · 通过

- 问句：按题目的题型ID统计题目数量
- 期望：`{"table": "tk001", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "Tm_tx_ID"}`
- 差异：`{}`

```sql
SELECT [Tm_tx_ID] AS [Tm_tx_ID], COUNT_BIG(*) AS [record_count] FROM [tk001] GROUP BY [Tm_tx_ID];
```

## exam

### exam-01 · 通过

- 问句：查询考试成绩记录
- 期望：`{"table": "clerk_kscj", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Clerk_kscj_ID], [Type], [clerk_ID], [Tk_cl_id], [Clerk_ks_status], [clerk_ks_btime], [clerk_ks_etime], [Cj] FROM [clerk_kscj];
```

### exam-02 · 通过

- 问句：统计考试报名数量
- 期望：`{"table": "Exam_Apply", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [Exam_Apply];
```

### exam-03 · 通过

- 问句：查询考试成绩的平均成绩
- 期望：`{"table": "clerk_kscj", "intent": "aggregate", "aggregation": "avg", "metric_column": "Cj"}`
- 差异：`{}`

```sql
SELECT AVG([Cj]) AS [avg_Cj] FROM [clerk_kscj];
```

### exam-04 · 通过

- 问句：查询状态为1的考试报名记录
- 期望：`{"table": "Exam_Apply", "intent": "list", "filters": {"Status": 1}}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Status], [CreateTime], [StudentId], [ExamId], [AuditorId], [AuditTime], [SerialNo] FROM [Exam_Apply] WHERE [Status] = ?;
```

## training

### training-01 · 通过

- 问句：查询课程记录
- 期望：`{"table": "Course_Info", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Name], [Status], [CreatedTime], [UserId], [CourseCategoryId], [Lectuer], [Description] FROM [Course_Info];
```

### training-02 · 通过

- 问句：按状态统计学习班数量
- 期望：`{"table": "Study_Class_Info", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "Status"}`
- 差异：`{}`

```sql
SELECT [Status] AS [Status], COUNT_BIG(*) AS [record_count] FROM [Study_Class_Info] GROUP BY [Status];
```

### training-03 · 通过

- 问句：查询课程的平均学分
- 期望：`{"table": "Course_Info", "intent": "aggregate", "aggregation": "avg", "metric_column": "CreditHour"}`
- 差异：`{}`

```sql
SELECT AVG([CreditHour]) AS [avg_CreditHour] FROM [Course_Info];
```

### training-04 · 通过

- 问句：查询课程学分最高的前5个课程名称
- 期望：`{"table": "Course_Info", "intent": "top_n", "aggregation": "sum", "metric_column": "CreditHour", "dimension_column": "Name", "limit": 5, "order": "desc"}`
- 差异：`{}`

```sql
SELECT TOP (5) [Name] AS [Name], SUM([CreditHour]) AS [sum_CreditHour] FROM [Course_Info] GROUP BY [Name] ORDER BY [sum_CreditHour] DESC;
```

## forum

### forum-01 · 通过

- 问句：查询论坛版块记录
- 期望：`{"table": "BBSBoardInfo", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [CreateTime], [UserId], [BordName], [MasterIDList], [MasterNameList], [Notes], [Creator] FROM [BBSBoardInfo];
```

### forum-02 · 通过

- 问句：统计论坛主题数量
- 期望：`{"table": "BBSTopicInfo", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [BBSTopicInfo];
```

### forum-03 · 通过

- 问句：查询回帖记录
- 期望：`{"table": "BBSReplayInfo", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [TopicID], [Subject], [IpAddress], [Creator], [PostTime], [IsBest], [Weight] FROM [BBSReplayInfo];
```

## configuration

### configuration-01 · 通过

- 问句：查询企业用户配置记录
- 期望：`{"table": "User_Option_Info", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Type], [UserId], [OptionName], [OptionValue], [Notes], [SerialNo] FROM [User_Option_Info];
```

### configuration-02 · 通过

- 问句：统计企业用户配置数量
- 期望：`{"table": "User_Option_Info", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [User_Option_Info];
```

### configuration-03 · 通过

- 问句：按类型统计企业用户配置数量
- 期望：`{"table": "User_Option_Info", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "Type"}`
- 差异：`{}`

```sql
SELECT [Type] AS [Type], COUNT_BIG(*) AS [record_count] FROM [User_Option_Info] GROUP BY [Type];
```

## notification

### notification-01 · 通过

- 问句：查询Email邮件记录
- 期望：`{"table": "Email_Info", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [ID], [Status], [CreateTime], [StudentName], [StudentActualName], [StudentEmail], [Subject], [MessageBody] FROM [Email_Info];
```

### notification-02 · 通过

- 问句：统计站内邮件收件人信息数量
- 期望：`{"table": "Sys_Mail_Receivers_Info", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [Sys_Mail_Receivers_Info];
```

### notification-03 · 通过

- 问句：查询站内邮件记录
- 期望：`{"table": "Sys_Mail_Info", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [CreateTime], [Subject], [Content], [Author], [MsgType], [IsAuthorDelete], [SerialNo] FROM [Sys_Mail_Info];
```

## system

### system-01 · 通过

- 问句：查询角色记录
- 期望：`{"table": "Role_Info", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [NAME], [USERID], [SERIALNO] FROM [Role_Info];
```

### system-02 · 通过

- 问句：统计系统权限数量
- 期望：`{"table": "Sys_Access_Info", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [Sys_Access_Info];
```

### system-03 · 通过

- 问句：查询本月创建的群组
- 期望：`{"table": "Group_Info", "intent": "list", "time_field": "CreateTime"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Name], [CreateTime], [Note], [CreatorId], [UserId], [SerialNo] FROM [Group_Info] WHERE [CreateTime] >= ? AND [CreateTime] < ?;
```

## news

### news-01 · 通过

- 问句：查询新闻资讯记录
- 期望：`{"table": "News_Info", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Status], [CreatedTime], [NewsTypeId], [Subject], [MessageBody], [ImageUrl], [ImageFlag] FROM [News_Info];
```

### news-02 · 通过

- 问句：统计新闻栏目数量
- 期望：`{"table": "News_Type_Info", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [News_Type_Info];
```

### news-03 · 通过

- 问句：按栏目类型标识统计新闻资讯数量
- 期望：`{"table": "News_Info", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "NewsTypeId"}`
- 差异：`{}`

```sql
SELECT [NewsTypeId] AS [NewsTypeId], COUNT_BIG(*) AS [record_count] FROM [News_Info] GROUP BY [NewsTypeId];
```

## evaluation

### evaluation-01 · 通过

- 问句：查询考评活动记录
- 期望：`{"table": "Evaluation", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Title], [CreateTime], [BeginTime], [EndTime], [Subject], [LimitedTime], [UserId] FROM [Evaluation];
```

### evaluation-02 · 通过

- 问句：统计考评活动专家数量
- 期望：`{"table": "Evaluation_Expert", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [Evaluation_Expert];
```

### evaluation-03 · 通过

- 问句：按状态统计评分记录数量
- 期望：`{"table": "Evaluation_Result", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "Status"}`
- 差异：`{}`

```sql
SELECT [Status] AS [Status], COUNT_BIG(*) AS [record_count] FROM [Evaluation_Result] GROUP BY [Status];
```

## game

### game-01 · 通过

- 问句：查询闯关游戏主题记录
- 期望：`{"table": "GameInfo", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Title], [Status], [CreatedTime], [Notes], [ImageUrl], [UserId], [CreatorId] FROM [GameInfo];
```

### game-02 · 通过

- 问句：统计闯关游戏参加人员安排数量
- 期望：`{"table": "GameArrangeInfo", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [GameArrangeInfo];
```

### game-03 · 通过

- 问句：按状态统计员工游戏情况数量
- 期望：`{"table": "GameStudentInfo", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "Status"}`
- 差异：`{}`

```sql
SELECT [Status] AS [Status], COUNT_BIG(*) AS [record_count] FROM [GameStudentInfo] GROUP BY [Status];
```

## skill_matrix

### skill-01 · 通过

- 问句：查询能力记录
- 期望：`{"table": "Skill_Info", "intent": "list"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Name], [CreateTime], [Description], [SkillCategoryId], [SerialNo], [CreatorId] FROM [Skill_Info];
```

### skill-02 · 通过

- 问句：统计能力等级数量
- 期望：`{"table": "Skill_Level_Info", "intent": "count", "aggregation": "count"}`
- 差异：`{}`

```sql
SELECT COUNT_BIG(*) AS [record_count] FROM [Skill_Level_Info];
```

### skill-03 · 通过

- 问句：按评定来源统计员工能力数量
- 期望：`{"table": "Student_Skill_Info", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "SourceType"}`
- 差异：`{}`

```sql
SELECT [SourceType] AS [SourceType], COUNT_BIG(*) AS [record_count] FROM [Student_Skill_Info] GROUP BY [SourceType];
```

### skill-04 · 通过

- 问句：查询本月能力变更日志
- 期望：`{"table": "Student_Skill_History_Info", "intent": "list", "time_field": "CreateTime"}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [CreateTime], [StudentId], [SkillId], [SkillLevelIId], [ObjectType], [ObjectId], [SerialNo] FROM [Student_Skill_History_Info] WHERE [CreateTime] >= ? AND [CreateTime] < ?;
```

## exam

### complex-01 · 通过

- 问句：查询张三所有的考试报名记录
- 期望：`{"table": "Exam_Apply", "intent": "list", "filters": {"Student_Info.ActualName": "张三"}, "join_tables": ["Student_Info"], "join_count": 1, "sql_contains": ["INNER JOIN [Student_Info]", "[t1].[ActualName] = ?"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Status], [t0].[CreateTime], [t0].[StudentId], [t0].[ExamId], [t0].[AuditorId], [t0].[AuditTime], [t0].[SerialNo] FROM [Exam_Apply] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] WHERE [t1].[ActualName] = ?;
```

### complex-02 · 通过

- 问句：查询李四的考试成绩
- 期望：`{"table": "clerk_kscj", "intent": "list", "filters": {"Student_Info.ActualName": "李四"}, "join_tables": ["Exam_Start", "Student_Info"], "join_count": 2}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Clerk_kscj_ID], [t0].[Type], [t0].[clerk_ID], [t0].[Tk_cl_id], [t0].[Clerk_ks_status], [t0].[clerk_ks_btime], [t0].[clerk_ks_etime], [t0].[Cj] FROM [clerk_kscj] AS [t0] INNER JOIN [Exam_Start] AS [t1] ON [t0].[ExamStartId] = [t1].[Id] INNER JOIN [Student_Info] AS [t2] ON [t1].[StudentId] = [t2].[Id] WHERE [t2].[ActualName] = ?;
```

### complex-03 · 通过

- 问句：按部门统计考试报名数量
- 期望：`{"table": "Exam_Apply", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "Department", "dimension_table": "Student_Info", "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT [t1].[Department] AS [Department], COUNT_BIG(*) AS [record_count] FROM [Exam_Apply] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] GROUP BY [t1].[Department];
```

### complex-04 · 通过

- 问句：查询本月张三状态为1的考试报名记录
- 期望：`{"table": "Exam_Apply", "intent": "list", "filters": {"Exam_Apply.Status": 1, "Student_Info.ActualName": "张三"}, "time_field": "CreateTime", "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Status], [t0].[CreateTime], [t0].[StudentId], [t0].[ExamId], [t0].[AuditorId], [t0].[AuditTime], [t0].[SerialNo] FROM [Exam_Apply] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] WHERE [t0].[Status] = ? AND [t1].[ActualName] = ? AND [t0].[CreateTime] >= ? AND [t0].[CreateTime] < ?;
```

## account

### complex-05 · 通过

- 问句：查询研发部所有学员
- 期望：`{"table": "Student_Info", "intent": "list", "filters": {"Student_Info.Department": "研发部"}, "join_count": 0}`
- 差异：`{}`

```sql
SELECT TOP (100) [Id], [Name], [ActualName], [Status], [CreatedTime], [UserId], [Password], [Degree] FROM [Student_Info] WHERE [Department] = ?;
```

## training

### complex-06 · 通过

- 问句：查询参加年度培训课程的学员名单
- 期望：`{"table": "Student_Info", "intent": "list", "filters": {"Course_Info.Name": "年度培训"}, "join_tables": ["Course_Info", "Student_CourseInfo"], "join_count": 2}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Name], [t0].[ActualName], [t0].[Status], [t0].[CreatedTime], [t0].[UserId], [t0].[Password], [t0].[Degree] FROM [Student_Info] AS [t0] INNER JOIN [Student_CourseInfo] AS [t1] ON [t1].[StudentId] = [t0].[Id] INNER JOIN [Course_Info] AS [t2] ON [t1].[CourseId] = [t2].[Id] WHERE [t2].[Name] = ?;
```

### complex-07 · 通过

- 问句：查询张三参加的学习班
- 期望：`{"table": "Study_Class_Info", "intent": "list", "filters": {"Student_Info.ActualName": "张三"}, "join_tables": ["Student_Info", "Study_Class_Student_Info"], "join_count": 2}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Name], [t0].[Status], [t0].[CreatedTime], [t0].[UserId], [t0].[CreditHour], [t0].[Periods], [t0].[HavingExamination] FROM [Study_Class_Info] AS [t0] INNER JOIN [Study_Class_Student_Info] AS [t1] ON [t1].[StudyClassId] = [t0].[Id] INNER JOIN [Student_Info] AS [t2] ON [t1].[StudentId] = [t2].[Id] WHERE [t2].[ActualName] = ?;
```

## skill_matrix

### complex-08 · 通过

- 问句：查询姓名为王五的员工能力记录
- 期望：`{"table": "Student_Skill_Info", "intent": "list", "filters": {"Student_Info.ActualName": "王五"}, "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[StudentId], [t0].[SkillId], [t0].[SkillLevelId], [t0].[AssessedDate], [t0].[AssessorId], [t0].[SourceType], [t0].[ProofData] FROM [Student_Skill_Info] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] WHERE [t1].[ActualName] = ?;
```

## game

### complex-09 · 通过

- 问句：按部门统计员工游戏情况数量
- 期望：`{"table": "GameStudentInfo", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "Department", "dimension_table": "Student_Info", "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT [t1].[Department] AS [Department], COUNT_BIG(*) AS [record_count] FROM [GameStudentInfo] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] GROUP BY [t1].[Department];
```

## skill_matrix

### complex-10 · 通过

- 问句：查询部门为培训部的能力变更日志
- 期望：`{"table": "Student_Skill_History_Info", "intent": "list", "filters": {"Student_Info.Department": "培训部"}, "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[CreateTime], [t0].[StudentId], [t0].[SkillId], [t0].[SkillLevelIId], [t0].[ObjectType], [t0].[ObjectId], [t0].[SerialNo] FROM [Student_Skill_History_Info] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] WHERE [t1].[Department] = ?;
```

## training

### complex-11 · 通过

- 问句：查询课程名称为安全生产的学员学习课程日志
- 期望：`{"table": "Student_Course_Log", "intent": "list", "filters": {"Course_Info.Name": "安全生产"}, "join_tables": ["Course_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[BeginTime], [t0].[EndTime], [t0].[UserId], [t0].[StudentId], [t0].[CourseId], [t0].[SerialNo] FROM [Student_Course_Log] AS [t0] INNER JOIN [Course_Info] AS [t1] ON [t0].[CourseId] = [t1].[Id] WHERE [t1].[Name] = ?;
```

### complex-12 · 通过

- 问句：查询用户名为zhangsan的积分日志
- 期望：`{"table": "Student_Point_Log", "intent": "list", "filters": {"Student_Info.Name": "zhangsan"}, "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[CreateTime], [t0].[StudentId], [t0].[ActionID], [t0].[PointNum], [t0].[LinkObject], [t0].[SerialNo] FROM [Student_Point_Log] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] WHERE [t1].[Name] = ?;
```

### complex-13 · 通过

- 问句：查询去年部门为生产部的面授课程讨论信息
- 期望：`{"table": "OffTrain_Discuss_Info", "intent": "list", "filters": {"Student_Info.Department": "生产部"}, "time_field": "CreateTime", "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Status], [t0].[CreateTime], [t0].[OfftrainId], [t0].[StudentId], [t0].[Content], [t0].[SerialNo] FROM [OffTrain_Discuss_Info] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] WHERE [t1].[Department] = ? AND [t0].[CreateTime] >= ? AND [t0].[CreateTime] < ?;
```

## game

### complex-14 · 通过

- 问句：按真实姓名统计闯关游戏参加人员数量
- 期望：`{"table": "GameArrangeInfo", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "ActualName", "dimension_table": "Student_Info", "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT [t1].[ActualName] AS [ActualName], COUNT_BIG(*) AS [record_count] FROM [GameArrangeInfo] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] GROUP BY [t1].[ActualName];
```

## training

### complex-15 · 通过

- 问句：查询学员姓名为陈晨的学员课件学习记录
- 期望：`{"table": "Student_Courseware_Info", "intent": "list", "filters": {"Student_Info.ActualName": "陈晨"}, "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Status], [t0].[CoursewareId], [t0].[StudentId], [t0].[SerialNo], [t0].[StudyTime] FROM [Student_Courseware_Info] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] WHERE [t1].[ActualName] = ?;
```

### complex-16 · 通过

- 问句：查询学习班名称为管理提升班的学习班报名申请记录
- 期望：`{"table": "Study_Class_Apply_Info", "intent": "list", "filters": {"Study_Class_Info.Name": "管理提升班"}, "join_tables": ["Study_Class_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Status], [t0].[StudyClassID], [t0].[StudentId], [t0].[AuditorId], [t0].[AuditTime], [t0].[SerialNo] FROM [Study_Class_Apply_Info] AS [t0] INNER JOIN [Study_Class_Info] AS [t1] ON [t0].[StudyClassID] = [t1].[Id] WHERE [t1].[Name] = ?;
```

### complex-17 · 通过

- 问句：查询线下培训为应急演练的学员离线学习班学习记录
- 期望：`{"table": "Student_OffTrain_Info", "intent": "list", "filters": {"OffTrain_Info.Name": "应急演练"}, "join_tables": ["OffTrain_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Status], [t0].[StudentId], [t0].[OffTrainId], [t0].[BeginDate], [t0].[EndDate], [t0].[SerialNo] FROM [Student_OffTrain_Info] AS [t0] INNER JOIN [OffTrain_Info] AS [t1] ON [t0].[OffTrainId] = [t1].[Id] WHERE [t1].[Name] = ?;
```

## skill_matrix

### complex-18 · 通过

- 问句：查询能力名称为数据分析的员工能力记录
- 期望：`{"table": "Student_Skill_Info", "intent": "list", "filters": {"Skill_Info.Name": "数据分析"}, "join_tables": ["Skill_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[StudentId], [t0].[SkillId], [t0].[SkillLevelId], [t0].[AssessedDate], [t0].[AssessorId], [t0].[SourceType], [t0].[ProofData] FROM [Student_Skill_Info] AS [t0] INNER JOIN [Skill_Info] AS [t1] ON [t0].[SkillId] = [t1].[Id] WHERE [t1].[Name] = ?;
```

## training

### complex-19 · 通过

- 问句：按课程名称统计课程选修情况设定数量
- 期望：`{"table": "Elective_Info", "intent": "group_aggregate", "aggregation": "count", "dimension_column": "Name", "dimension_table": "Course_Info", "join_tables": ["Course_Info"]}`
- 差异：`{}`

```sql
SELECT [t1].[Name] AS [Name], COUNT_BIG(*) AS [record_count] FROM [Elective_Info] AS [t0] INNER JOIN [Course_Info] AS [t1] ON [t0].[CourseId] = [t1].[Id] GROUP BY [t1].[Name];
```

## exam

### complex-20 · 通过

- 问句：查询近30天学员姓名为赵敏且状态为1的考试报名记录
- 期望：`{"table": "Exam_Apply", "intent": "list", "filters": {"Exam_Apply.Status": 1, "Student_Info.ActualName": "赵敏"}, "time_field": "CreateTime", "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Status], [t0].[CreateTime], [t0].[StudentId], [t0].[ExamId], [t0].[AuditorId], [t0].[AuditTime], [t0].[SerialNo] FROM [Exam_Apply] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] WHERE [t0].[Status] = ? AND [t1].[ActualName] = ? AND [t0].[CreateTime] >= ? AND [t0].[CreateTime] < ?;
```

### complex-21 · 通过

- 问句：考试报名数量排名前5的部门
- 期望：`{"table": "Exam_Apply", "intent": "top_n", "aggregation": "count", "dimension_column": "Department", "dimension_table": "Student_Info", "limit": 5, "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (5) [t1].[Department] AS [Department], COUNT_BIG(*) AS [record_count] FROM [Exam_Apply] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] GROUP BY [t1].[Department] ORDER BY [record_count] DESC;
```

## training

### complex-22 · 通过

- 问句：查询张三参加的课程
- 期望：`{"table": "Course_Info", "intent": "list", "filters": {"Student_Info.ActualName": "张三"}, "join_tables": ["Student_CourseInfo", "Student_Info"], "join_count": 2}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[Name], [t0].[Status], [t0].[CreatedTime], [t0].[UserId], [t0].[CourseCategoryId], [t0].[Lectuer], [t0].[Description] FROM [Course_Info] AS [t0] INNER JOIN [Student_CourseInfo] AS [t1] ON [t1].[CourseId] = [t0].[Id] INNER JOIN [Student_Info] AS [t2] ON [t1].[StudentId] = [t2].[Id] WHERE [t2].[ActualName] = ?;
```

## system

### complex-23 · 通过

- 问句：查询学员姓名为刘洋的学员获取证书记录
- 期望：`{"table": "Student_Certificate_Info", "intent": "list", "filters": {"Student_Info.ActualName": "刘洋"}, "join_tables": ["Student_Info"]}`
- 差异：`{}`

```sql
SELECT TOP (100) [t0].[Id], [t0].[StudentId], [t0].[CertificateId], [t0].[CertificateName], [t0].[CertificateNumber], [t0].[Organization], [t0].[AwardTime], [t0].[Tk_Cl_Id] FROM [Student_Certificate_Info] AS [t0] INNER JOIN [Student_Info] AS [t1] ON [t0].[StudentId] = [t1].[Id] WHERE [t1].[ActualName] = ?;
```

## training

### report-01 · 通过

- 问句：2026年度各部门一至十二月份人均学习时长横向对比
- 期望：`{"report_type": "department_monthly_per_capita_learning_hours", "table": "Student_Course_Log", "intent": "cross_tab", "aggregation": "per_capita_hours", "dimension_column": "Department", "dimension_table": "Student_Info", "date_start": "2026-01-01", "date_end": "2027-01-01", "filters": {"Student_Info.Status": 1}, "join_tables": ["Student_Info"], "sql_contains": ["LEFT JOIN [Student_Course_Log]", "COUNT(DISTINCT [s].[Id])", "[1月人均学习时长_小时]", "[12月人均学习时长_小时]"]}`
- 差异：`{}`

```sql
SELECT [s].[Department] AS [Department], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 1 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [1月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 2 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [2月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 3 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [3月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 4 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [4月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 5 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [5月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 6 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [6月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 7 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [7月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 8 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [8月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 9 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [9月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 10 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [10月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 11 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [11月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 12 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [12月人均学习时长_小时] FROM [Student_Info] AS [s] LEFT JOIN [Student_Course_Log] AS [l] ON [s].[Id] = [l].[StudentId] AND [l].[BeginTime] >= ? AND [l].[BeginTime] < ? WHERE [s].[Status] = ? GROUP BY [s].[Department] ORDER BY [s].[Department] ASC;
```

### report-02 · 通过

- 问句：2025年不同部门每个月平均每人培训学时趋势报表
- 期望：`{"report_type": "department_monthly_per_capita_learning_hours", "intent": "cross_tab", "date_start": "2025-01-01", "date_end": "2026-01-01", "metric_unit": "hour"}`
- 差异：`{}`

```sql
SELECT [s].[Department] AS [Department], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 1 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [1月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 2 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [2月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 3 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [3月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 4 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [4月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 5 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [5月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 6 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [6月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 7 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [7月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 8 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [8月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 9 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [9月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 10 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [10月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 11 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [11月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 12 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [12月人均学习时长_小时] FROM [Student_Info] AS [s] LEFT JOIN [Student_Course_Log] AS [l] ON [s].[Id] = [l].[StudentId] AND [l].[BeginTime] >= ? AND [l].[BeginTime] < ? WHERE [s].[Status] = ? GROUP BY [s].[Department] ORDER BY [s].[Department] ASC;
```

### report-03 · 通过

- 问句：各部门2024全年逐月员工人均课程学习时间对比表
- 期望：`{"report_type": "department_monthly_per_capita_learning_hours", "intent": "cross_tab", "date_start": "2024-01-01", "date_end": "2025-01-01", "secondary_dimension": "MONTH(Student_Course_Log.BeginTime)"}`
- 差异：`{}`

```sql
SELECT [s].[Department] AS [Department], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 1 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [1月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 2 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [2月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 3 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [3月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 4 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [4月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 5 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [5月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 6 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [6月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 7 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [7月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 8 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [8月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 9 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [9月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 10 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [10月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 11 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [11月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 12 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [12月人均学习时长_小时] FROM [Student_Info] AS [s] LEFT JOIN [Student_Course_Log] AS [l] ON [s].[Id] = [l].[StudentId] AND [l].[BeginTime] >= ? AND [l].[BeginTime] < ? WHERE [s].[Status] = ? GROUP BY [s].[Department] ORDER BY [s].[Department] ASC;
```

### report-04 · 通过

- 问句：2023年度按部门月度每人平均学习用时汇总
- 期望：`{"report_type": "department_monthly_per_capita_learning_hours", "intent": "cross_tab", "date_start": "2023-01-01", "date_end": "2024-01-01", "aggregation": "per_capita_hours"}`
- 差异：`{}`

```sql
SELECT [s].[Department] AS [Department], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 1 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [1月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 2 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [2月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 3 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [3月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 4 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [4月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 5 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [5月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 6 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [6月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 7 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [7月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 8 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [8月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 9 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [9月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 10 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [10月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 11 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [11月人均学习时长_小时], ROUND(COALESCE(CAST(SUM(CASE WHEN MONTH([l].[BeginTime]) = 12 AND [l].[EndTime] >= [l].[BeginTime] THEN CAST(DATEDIFF(SECOND, [l].[BeginTime], [l].[EndTime]) AS bigint) ELSE CAST(0 AS bigint) END) AS decimal(38,2)) / NULLIF(COUNT(DISTINCT [s].[Id]), 0) / 3600.0, 0), 2) AS [12月人均学习时长_小时] FROM [Student_Info] AS [s] LEFT JOIN [Student_Course_Log] AS [l] ON [s].[Id] = [l].[StudentId] AND [l].[BeginTime] >= ? AND [l].[BeginTime] < ? WHERE [s].[Status] = ? GROUP BY [s].[Department] ORDER BY [s].[Department] ASC;
```

### report-05 · 通过

- 问句：2026年度各部门每月学习时长中位数对比
- 期望：`{"error_contains": "当前没有匹配到已审核的KPI规则"}`
- 差异：`{}`

```sql
-- 未生成 SQL
```

## exam

### score-01 · 通过

- 问句：2026年张三和李四各自在线性代数中取得的最高分
- 期望：`{"report_type": "student_exam_score_aggregate", "fact": "exam_score", "table": "clerk_kscj", "intent": "group_aggregate", "aggregation": "max", "metric_column": "Cj", "dimension_column": "ActualName", "date_start": "2026-01-01", "date_end": "2027-01-01", "filters": {"Student_Info.ActualName": ["张三", "李四"], "Course_Info.Name": "线性代数", "clerk_kscj.Clerk_ks_status": 1}, "join_tables": ["Course_Info", "Exam_Start", "Student_Info", "tk_cl"], "join_count": 4, "sql_contains": ["MAX([k].[Cj])", "[s].[ActualName] IN (?, ?)", "CONVERT(varchar(50), [p].[SiteID]) = [c].[Id]", "[p].[SiteType] IN (1, 3)"]}`
- 差异：`{}`

```sql
SELECT [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], MAX([k].[Cj]) AS [max_score] FROM [clerk_kscj] AS [k] INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id] INNER JOIN [tk_cl] AS [p] ON [k].[Tk_cl_id] = [p].[Tk_cl_id] INNER JOIN [Course_Info] AS [c] ON CONVERT(varchar(50), [p].[SiteID]) = [c].[Id] AND [p].[SiteType] IN (1, 3) WHERE [s].[ActualName] IN (?, ?) AND [c].[Name] = ? AND [k].[clerk_ks_btime] >= ? AND [k].[clerk_ks_btime] < ? AND [k].[Clerk_ks_status] = ? AND [k].[Cj] IS NOT NULL GROUP BY [s].[Id], [s].[ActualName] ORDER BY [s].[ActualName] ASC;
```

### score-02 · 通过

- 问句：查询2025年度王五与赵敏分别在高等数学课程中的最低成绩
- 期望：`{"report_type": "student_exam_score_aggregate", "aggregation": "min", "date_start": "2025-01-01", "date_end": "2026-01-01", "filters": {"Student_Info.ActualName": ["王五", "赵敏"], "Course_Info.Name": "高等数学"}, "sql_contains": ["MIN([k].[Cj])", "[min_score]"]}`
- 差异：`{}`

```sql
SELECT [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], MIN([k].[Cj]) AS [min_score] FROM [clerk_kscj] AS [k] INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id] INNER JOIN [tk_cl] AS [p] ON [k].[Tk_cl_id] = [p].[Tk_cl_id] INNER JOIN [Course_Info] AS [c] ON CONVERT(varchar(50), [p].[SiteID]) = [c].[Id] AND [p].[SiteType] IN (1, 3) WHERE [s].[ActualName] IN (?, ?) AND [c].[Name] = ? AND [k].[clerk_ks_btime] >= ? AND [k].[clerk_ks_btime] < ? AND [k].[Clerk_ks_status] = ? AND [k].[Cj] IS NOT NULL GROUP BY [s].[Id], [s].[ActualName] ORDER BY [s].[ActualName] ASC;
```

### score-03 · 通过

- 问句：统计张三、李四以及王五各人2024全年在课程名称为数据分析的考试中的平均分
- 期望：`{"report_type": "student_exam_score_aggregate", "aggregation": "avg", "filters": {"Student_Info.ActualName": ["张三", "李四", "王五"], "Course_Info.Name": "数据分析"}, "sql_contains": ["AVG([k].[Cj])", "IN (?, ?, ?)"]}`
- 差异：`{}`

```sql
SELECT [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], AVG([k].[Cj]) AS [avg_score] FROM [clerk_kscj] AS [k] INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id] INNER JOIN [tk_cl] AS [p] ON [k].[Tk_cl_id] = [p].[Tk_cl_id] INNER JOIN [Course_Info] AS [c] ON CONVERT(varchar(50), [p].[SiteID]) = [c].[Id] AND [p].[SiteType] IN (1, 3) WHERE [s].[ActualName] IN (?, ?, ?) AND [c].[Name] = ? AND [k].[clerk_ks_btime] >= ? AND [k].[clerk_ks_btime] < ? AND [k].[Clerk_ks_status] = ? AND [k].[Cj] IS NOT NULL GROUP BY [s].[Id], [s].[ActualName] ORDER BY [s].[ActualName] ASC;
```

### score-04 · 通过

- 问句：2026年张三和李四各自最高分
- 期望：`{"report_type": "student_exam_score_aggregate", "aggregation": "max", "join_tables": ["Exam_Start", "Student_Info"], "join_count": 2, "date_start": "2026-01-01", "date_end": "2027-01-01"}`
- 差异：`{}`

```sql
SELECT [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], MAX([k].[Cj]) AS [max_score] FROM [clerk_kscj] AS [k] INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id] WHERE [s].[ActualName] IN (?, ?) AND [k].[clerk_ks_btime] >= ? AND [k].[clerk_ks_btime] < ? AND [k].[Clerk_ks_status] = ? AND [k].[Cj] IS NOT NULL GROUP BY [s].[Id], [s].[ActualName] ORDER BY [s].[ActualName] ASC;
```

### score-05 · 通过

- 问句：2026年张三和李四在线性代数中的最高分
- 期望：`{"error_contains": "没有明确是分别统计还是合并统计"}`
- 差异：`{}`

```sql
-- 未生成 SQL
```

## system

### score-06 · 通过

- 问句：查询量子涨落熵系数
- 期望：`{"error_contains": "目标事实表无法可靠识别"}`
- 差异：`{}`

```sql
-- 未生成 SQL
```

## exam

### ranking-01 · 通过

- 问句：2026年所有课程平均成绩最高的10个学生
- 期望：`{"report_type": "student_exam_score_ranking", "fact": "exam_score", "table": "clerk_kscj", "intent": "top_n", "aggregation": "avg", "metric_column": "Cj", "dimension_column": "ActualName", "limit": 10, "order": "desc", "date_start": "2026-01-01", "date_end": "2027-01-01", "filters": {"clerk_kscj.Clerk_ks_status": 1}, "join_tables": ["Course_Info", "Exam_Start", "Student_Info", "tk_cl"], "join_count": 4, "sql_contains": ["SELECT TOP (10)", "AVG([k].[Cj]) AS [avg_score]", "[p].[SiteType] IN (1, 3)", "ORDER BY [avg_score] DESC"]}`
- 差异：`{}`

```sql
SELECT TOP (10) [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], AVG([k].[Cj]) AS [avg_score] FROM [clerk_kscj] AS [k] INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id] INNER JOIN [tk_cl] AS [p] ON [k].[Tk_cl_id] = [p].[Tk_cl_id] INNER JOIN [Course_Info] AS [c] ON CONVERT(varchar(50), [p].[SiteID]) = [c].[Id] AND [p].[SiteType] IN (1, 3) WHERE [k].[clerk_ks_btime] >= ? AND [k].[clerk_ks_btime] < ? AND [k].[Clerk_ks_status] = ? AND [k].[Cj] IS NOT NULL GROUP BY [s].[Id], [s].[ActualName] ORDER BY [avg_score] DESC, [s].[ActualName] ASC, [s].[Id] ASC;
```

### ranking-02 · 通过

- 问句：2026年研发部所有课程平均成绩最高的10个学生
- 期望：`{"report_type": "student_exam_score_ranking", "aggregation": "avg", "limit": 10, "filters": {"Student_Info.Department": "研发部", "clerk_kscj.Clerk_ks_status": 1}, "sql_contains": ["[s].[Department] = ?", "GROUP BY [s].[Id], [s].[ActualName]"]}`
- 差异：`{}`

```sql
SELECT TOP (10) [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], AVG([k].[Cj]) AS [avg_score] FROM [clerk_kscj] AS [k] INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id] INNER JOIN [tk_cl] AS [p] ON [k].[Tk_cl_id] = [p].[Tk_cl_id] INNER JOIN [Course_Info] AS [c] ON CONVERT(varchar(50), [p].[SiteID]) = [c].[Id] AND [p].[SiteType] IN (1, 3) WHERE [s].[Department] = ? AND [k].[clerk_ks_btime] >= ? AND [k].[clerk_ks_btime] < ? AND [k].[Clerk_ks_status] = ? AND [k].[Cj] IS NOT NULL GROUP BY [s].[Id], [s].[ActualName] ORDER BY [avg_score] DESC, [s].[ActualName] ASC, [s].[Id] ASC;
```

### ranking-03 · 通过

- 问句：2025年度高等数学平均分最低的5名学员
- 期望：`{"report_type": "student_exam_score_ranking", "aggregation": "avg", "limit": 5, "order": "asc", "filters": {"Course_Info.Name": "高等数学"}, "sql_contains": ["SELECT TOP (5)", "ORDER BY [avg_score] ASC"]}`
- 差异：`{}`

```sql
SELECT TOP (5) [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], AVG([k].[Cj]) AS [avg_score] FROM [clerk_kscj] AS [k] INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id] INNER JOIN [tk_cl] AS [p] ON [k].[Tk_cl_id] = [p].[Tk_cl_id] INNER JOIN [Course_Info] AS [c] ON CONVERT(varchar(50), [p].[SiteID]) = [c].[Id] AND [p].[SiteType] IN (1, 3) WHERE [c].[Name] = ? AND [k].[clerk_ks_btime] >= ? AND [k].[clerk_ks_btime] < ? AND [k].[Clerk_ks_status] = ? AND [k].[Cj] IS NOT NULL GROUP BY [s].[Id], [s].[ActualName] ORDER BY [avg_score] ASC, [s].[ActualName] ASC, [s].[Id] ASC;
```

### ranking-04 · 通过

- 问句：2023年全部考试平均成绩排行榜前10名学员
- 期望：`{"report_type": "student_exam_score_ranking", "aggregation": "avg", "limit": 10, "join_tables": ["Exam_Start", "Student_Info"], "join_count": 2, "sql_contains": ["AVG([k].[Cj])", "ORDER BY [avg_score] DESC"]}`
- 差异：`{}`

```sql
SELECT TOP (10) [s].[Id] AS [StudentId], [s].[ActualName] AS [StudentName], AVG([k].[Cj]) AS [avg_score] FROM [clerk_kscj] AS [k] INNER JOIN [Exam_Start] AS [e] ON [k].[ExamStartId] = [e].[Id] INNER JOIN [Student_Info] AS [s] ON [e].[StudentId] = [s].[Id] WHERE [k].[clerk_ks_btime] >= ? AND [k].[clerk_ks_btime] < ? AND [k].[Clerk_ks_status] = ? AND [k].[Cj] IS NOT NULL GROUP BY [s].[Id], [s].[ActualName] ORDER BY [avg_score] DESC, [s].[ActualName] ASC, [s].[Id] ASC;
```

### ranking-05 · 通过

- 问句：2026年数学专业所有课程平均成绩最高的10个学生
- 期望：`{"error_contains": "Student_Info学员表没有专业字段"}`
- 差异：`{}`

```sql
-- 未生成 SQL
```

### ranking-06 · 通过

- 问句：2026年一年级所有课程平均成绩前10名学生
- 期望：`{"error_contains": "Student_Info学员表没有年级字段"}`
- 差异：`{}`

```sql
-- 未生成 SQL
```

### ranking-07 · 通过

- 问句：2026年软件学院全部课程平均分最高的5个学员
- 期望：`{"error_contains": "Student_Info学员表没有学院字段"}`
- 差异：`{}`

```sql
-- 未生成 SQL
```

### ranking-08 · 通过

- 问句：2026年三班所有课程平均成绩排名前10的学生
- 期望：`{"error_contains": "Student_Info学员表没有班级字段"}`
- 差异：`{}`

```sql
-- 未生成 SQL
```

## training

### ambiguity-01 · 通过

- 问句：陈晨的课件学习记录有哪些
- 期望：`{"error_contains": "课件学习记录”在设计书中存在两种口径"}`
- 差异：`{}`

```sql
-- 未生成 SQL
```