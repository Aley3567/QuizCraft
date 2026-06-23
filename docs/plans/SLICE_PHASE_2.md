# QuizCraft Phase 2 垂直切片实施计划

> 基于 PRD_PHASE2.md + DESIGN_DECISIONS.md，按垂直切片思路拆解
> 2026-06-23 | 依赖 Phase 1 全部 5 个切片

---

## 切片划分思路

### 核心原则

1. **第一条切片是 Phase 2 最小可用闭环**：自适应引擎的诊断 -> 教学 -> 再测试 -> 掌握/卡住状态机。这是 Phase 2 区别于 Phase 1 的根本卖点——系统不再被动等用户出题，而是主动诊断你哪里不会、用你的文档教你、确认你真懂了再放行。2 周内让 yufeng 体验到"系统替我决定学什么"。
2. **每条切片纵向贯穿**：状态机逻辑 + API + DB 模型 + 前端 UI 一条龙，不做"先把所有状态机写完再做 UI"的横向铺层。
3. **按价值递增**：自适应闭环（2.1）-> 错题变体（2.2）-> 考前突击（2.3）-> 学习看板+归档（2.4）-> 课程文件夹+场景标签（2.5）。核心差异化先跑通，全局视图和场景切换后补。
4. **跨 Phase 依赖**：所有切片依赖 Phase 1 切片 1.1-1.3（出题引擎、答题判分、FSRS 闪卡、Concept/Question 数据模型）。切片 2.1 额外依赖 1.2（出题参数控制，诊断题需要按 concept 出简单题）。切片 2.5 依赖 1.4（DOCX 解析，课程文件夹需支持多格式文档）。

### Phase 2 PRD 的 42 条 user stories 分布

| 切片 | 覆盖 stories | 说明 |
|------|-------------|------|
| 2.1 自适应引擎最小闭环 | 1, 2, 3, 4, 5, 6, 7, 9 | 诊断->教学->再测试状态机 + 掌握度地图 + 卡住检测 + 手动跳过 |
| 2.2 错题变体生成 | 33, 34, 35, 36, 37 | 手动+自动变体出题，换角度攻击薄弱概念 |
| 2.3 考前突击模式 | 10, 11, 12, 13, 14, 15, 16, 18, 19 | 设考试日期->自动规划->进度追踪->突击看板 |
| 2.4 学习看板与归档 | 20, 21, 22, 23, 24, 25, 26 | Kanban 视图 + 自动列移动 + 归档 + 仪表盘 |
| 2.5 课程文件夹与场景标签 | 27, 28, 29, 30, 31, 32, 38, 39, 40, 41, 42 | 多文档合并知识图谱 + 跨文档出题 + 考试/面试模式切换 |

---

## 切片 2.1：自适应引擎最小闭环

**目标**：yufeng 打开一份已上传的文档，系统对每个概念出 2-3 道诊断题，做对标记掌握进 FSRS 池，做错进入教学模式——先展示文档原文段落，再出验证题，循环直到掌握或卡住。这是 Phase 2 核心差异化卖点的最小化版本。

**用户价值**：做完这个切片后，yufeng 不再需要自己决定"学什么"——系统自动诊断哪里会哪里不会，不会的用课件原文教你，教完再考确认你真懂了。这是 Quizlet/Knowt 完全做不到的主动式学习。

**预估天数**：14 天

### 任务清单

**自适应状态机（4 天）**
- Concept 数据模型扩展：新增 `mastery_state` 枚举字段（Unknown / Diagnosing / Teaching / Re-testing / Mastered / Stuck），默认 Unknown
- 状态转换逻辑模块（纯函数，无 LLM）：定义所有合法转换 + 守卫条件
  - Unknown + 开始诊断 -> Diagnosing
  - Diagnosing + 全部诊断题答对 -> Mastered + 写入 FSRS 池
  - Diagnosing + 任一诊断题答错 -> Teaching
  - Teaching + 展示文档 + 验证题答对 -> Mastered + 写入 FSRS 池
  - Teaching + 验证题答错（失败次数 < 3）-> 回到 Teaching（换不同解释角度）
  - 连续 3 次再测试失败 -> Stuck
- 状态转换日志表：`MasteryTransition`（concept_id, from_state, to_state, trigger_event, timestamp）
- 单元测试覆盖 PRD Seam 1 全部 7 条用例（确定性状态机，mock 内容生成器）

**诊断会话 API（3 天）**
- POST /api/concepts/{id}/start-diagnostic：触发诊断，从 practice pool 按该 Concept 取 2-3 道简单题（Bloom Remember/Understand 层），创建 AdaptiveSession
- POST /api/adaptive-sessions/{id}/answer：提交诊断题答案，全部答完后触发状态转换
- GET /api/adaptive-sessions/{id}/state：返回当前状态 + 下一步动作（teach / re-test / mastered / stuck）
- 诊断题来源：复用 Phase 1 切片 1.2 的出题引擎，限定 difficulty=easy、bloom=Remember/Understand、按 concept 过滤
- 如果某 Concept 的 practice pool 题目不足 2 道，自动生成补齐（调用 Phase 1 出题引擎）

**教学模式（3 天）**
- Teaching 状态触发：LLM 根据 Concept + source_span 生成教学解释（引用文档原文段落）
- 教学内容 API：POST /api/concepts/{id}/teach（返回文档原文段落 + LLM 生成的解释）
- 验证题生成：LLM 基于 Concept 出 1 道 follow-up 题（不同于诊断题，Bloom Understand/Apply 层），带 source_span
- 验证题评分：复用 Phase 1 切片 1.2 的简答评分（如果是简答题）或即时判分（如果是选择题）
- 重复教学时换角度：记录已用解释 prompt，LLM 被要求用不同方式解释同一概念（类比 / 对比 / 举例 / 逐步推导）

**掌握度地图 + 手动覆盖（2 天）**
- GET /api/documents/{id}/mastery-map：返回所有 Concept 的 mastery_state + 进度百分比
- 前端掌握度地图：文档详情页新增 tab，树形/网格展示概念列表，颜色标注状态（灰=Unknown / 黄=进行中 / 绿=Mastered / 红=Stuck）
- POST /api/concepts/{id}/override：手动设置 mastery_state（如标记 "already know" 直接进 Mastered + FSRS 池）
- Stuck 状态 UI 提示：建议手动复习文档该章节或暂时跳过

**前端自适应会话界面（2 天）**
- 自适应学习入口：文档详情页新增"开始自适应学习"按钮
- 诊断阶段：逐题答题界面（复用 Phase 1 答题组件），答完显示诊断结果
- 教学阶段：先展示文档原文卡片 + LLM 解释，下方出验证题
- 再测试阶段：新验证题，答完显示是否通过
- 状态流转全前端可见（进度指示器：诊断中 -> 教学中 -> 再测试 -> 掌握/卡住）

### 验收标准

- [ ] 打开已上传文档，点击"开始自适应学习"，系统对每个 Concept 出 2-3 道诊断题
- [ ] 诊断题全部答对的 Concept 标记为 Mastered，进入 FSRS 间隔重复池
- [ ] 诊断题答错的 Concept 进入教学模式，展示文档原文段落 + LLM 解释
- [ ] 教学后出验证题，答对则标记 Mastered，答错则换角度重新教学
- [ ] 连续 3 次再测试失败的 Concept 标记为 Stuck，UI 提示手动复习
- [ ] 掌握度地图展示所有 Concept 的状态（颜色区分），可手动标记跳过
- [ ] 状态机全部转换通过单元测试（7 条用例，确定性逻辑，无 LLM）

### 依赖

- Phase 1 切片 1.1（出题引擎、Concept/Question 数据模型、答题判分）
- Phase 1 切片 1.2（出题参数控制——诊断题需按 concept + difficulty + bloom 过滤）
- Phase 1 切片 1.3（FSRS 间隔重复池——掌握的概念需写入 FSRS）

---

## 切片 2.2：错题变体生成

**目标**：yufeng 做错一道题后，可以一键生成 2-3 道"换角度"变体题——不同题型、不同表述、针对同一概念和可能的误解。多次做错同一概念时系统自动生成变体并加入下次复习。

**用户价值**：做完这个切片后，yufeng 做错题不再只是"重做原题"——系统换一种题型、换一个角度重新考你同一概念，避免记住答案而非真正理解。这是"错题本"的正确打开方式：不是让你去看错题本，而是主动用新题攻击你的薄弱点。

**预估天数**：7 天

### 任务清单

**变体生成引擎（3 天）**
- 变体生成 prompt 工程：输入 = 原题 + 用户错误答案 + 正确答案 + Concept + source_span；输出 = 2-3 道新题
- 变体约束：题型必须不同于原题（如原题 MCQ -> 变体出 short_answer / fill_blank / scenario）；表述必须不同；必须 source-anchored；针对用户错误背后的可能误解
- 变体复用 Phase 1 自我批评管线（6 维度评分 + 淘汰阈值）
- Question 数据模型扩展：新增 `variant_of` 外键（指向原题 ID，可为空表示原创题）

**手动触发变体（2 天）**
- POST /api/questions/{id}/generate-variants：手动请求变体，返回 2-3 道新题
- 前端答题界面：错题反馈区新增"练习变体"按钮
- 变体答题流程：复用 Phase 1 答题组件，变体题答完后反馈仍引用文档原文
- 变体题与原题关联展示：UI 标注"此题源自 [原题编号]，针对同一概念换角度出题"

**自动触发 + 复习注入（2 天）**
- 错题计数：Answer 表统计每个 Concept 的错误次数
- 自动触发条件：某 Concept 累计错误 >= 3 次，自动调用变体生成引擎
- 自动生成的变体注入下次复习 session（FSRS review session 或自适应再测试 session）
- GET /api/concepts/{id}/variants：查看某概念的所有变体题 + 来源原题链
- 前端掌握度地图：Stuck / 高频错误 Concept 标记"已生成变体"标识

### 验收标准

- [ ] 做错一道选择题后，点击"练习变体"生成 2-3 道新题，题型不同于原题
- [ ] 变体题的反馈引用文档原文（source_span 有效）
- [ ] 变体题通过自我批评管线（低分题被淘汰）
- [ ] 变体题在 UI 标注源自哪道原题
- [ ] 同一 Concept 累计做错 3 次后，系统自动生成变体并加入下次复习
- [ ] 可查看某概念的所有变体题和原题关联链
- [ ] 变体生成通过集成测试（PRD Seam 4，LLM mock，验证编排逻辑）

### 依赖

- 切片 2.1（Concept 的 mastery_state + AdaptiveSession，变体注入再测试流程）
- Phase 1 切片 1.2（出题引擎 + 自我批评管线 + 简答评分）

---

## 切片 2.3：考前突击模式

**目标**：yufeng 设置考试日期，系统根据当前掌握度自动生成逐日学习计划（诊断->巩固->模拟考），跳过已掌握内容，动态调整进度，提供突击看板。

**用户价值**：做完这个切片后，yufeng 考前 3 天打开系统设个日期，系统直接告诉他"今天先诊断这 5 个概念、教这 3 个不会的，明天巩固，后天模拟考"。不用自己规划复习节奏，已掌握的自动跳过不浪费时间。

**预估天数**：10 天

### 任务清单

**学习规划器（4 天）**
- StudyPlan / DailyPlan / PlanTask 数据模型建表
  - StudyPlan: document_id/course_id, exam_date, created_at, status(active/completed/cancelled)
  - DailyPlan: study_plan_id, day_index, date, phase(diagnose/consolidate/mock_exam)
  - PlanTask: daily_plan_id, concept_ids[], task_type, status(pending/completed/skipped)
- 规划算法（纯逻辑，无 LLM，确定性）：
  - 输入：exam_date - today = available_days，各 Concept 的 mastery_state
  - 概念分类：Unknown（需完整诊断+教学）/ Weak（Diagnosing 或 Teaching 中）/ Mastered（已进 FSRS 池）
  - 按可用天数分配阶段（PRD 规划规则：1 天压缩版 / 2-3 天 / 4-7 天 / 7+ 天）
  - 每日任务生成：具体 Concept 列表 + session 类型（diagnostic/teaching/review/mock_exam）
- POST /api/study-plans：创建计划（传入 document_id + exam_date）
- 单元测试覆盖 PRD Seam 2 全部 6 条用例（纯逻辑，确定性）

**动态调整（2 天）**
- 计划执行 hook：每次 AdaptiveSession 完成后，检查当前 PlanTask 是否完成，更新状态
- 重新规划逻辑：每日结束时或 Concept 状态变化时，重新计算剩余天数 + 未完成概念，重新分配
- 如果 Day 1 提前完成所有诊断+教学 -> 把 Day 2 的巩固任务前移
- 如果落后进度 -> 压缩后续天数（减少模拟考天数，优先保证诊断+教学覆盖）
- POST /api/study-plans/{id}/recalculate：手动触发重新规划
- PUT /api/study-plans/{id}/exam-date：修改考试日期后自动重新规划

**每日任务执行（2 天）**
- GET /api/study-plans/{id}/today：返回今日任务列表（Concepts + session 类型）
- 今日任务与自适应引擎联动：diagnostic 类型 -> 调用切片 2.1 的诊断 API；teaching -> 教学模式；review -> FSRS 复习
- mock_exam 类型：从所有 Concept 的 practice pool 交叉混合出题，组成一套模拟卷
- PlanTask 完成标记：session 结束后自动标记 completed

**突击看板（2 天）**
- GET /api/study-plans/{id}/dashboard：返回突击看板数据
  - 距离考试天数
  - 已掌握 Concept 数 / 总数（进度条）
  - 预估就绪度分数（mastered / total * 100，加权考虑 Stuck 概念扣分）
  - 今日任务列表 + 完成状态
  - 各阶段完成进度
- 前端突击看板页：倒计时 + 进度环 + 今日任务卡片 + 阶段时间线
- 首页增加活跃突击计划入口（如有）

### 验收标准

- [ ] 设置考试日期（如 3 天后），系统自动生成逐日学习计划
- [ ] Day 1 计划包含诊断+教学任务，针对 Unknown 状态的 Concept
- [ ] 已 Mastered 的 Concept 不出现在计划中（跳过）
- [ ] 每日任务完成后自动标记，进度条更新
- [ ] 提前完成当日任务时，后续天数内容前移
- [ ] 修改考试日期后计划自动重新计算
- [ ] 突击看板显示倒计时、掌握进度、就绪度分数、今日任务
- [ ] 规划器全部用例通过单元测试（PRD Seam 2，纯逻辑，确定性）

### 依赖

- 切片 2.1（自适应引擎——诊断/教学/再测试是计划执行的核心）
- 切片 2.2（变体生成——巩固阶段对薄弱概念用变体题强化）
- Phase 1 切片 1.3（FSRS 复习——巩固阶段包含 FSRS 间隔复习）

---

## 切片 2.4：学习看板与归档

**目标**：全局 Kanban 视图展示所有文档/课程的学习状态（待学/进行中/已掌握），自动按掌握度移动列，支持手动拖拽覆盖和一键归档。首页仪表盘汇总学习数据。

**用户价值**：做完这个切片后，yufeng 打开系统第一眼就能看到"哪门课还没开始、哪门在学、哪门搞定了"，考完的课一键归档不再干扰，首页显示今日到期卡片数和连续学习天数——有动力有全局感。

**预估天数**：8 天

### 任务清单

**Kanban 状态推导（2 天）**
- Document / Course 数据模型扩展：新增 `kanban_override` 字段（可为空，手动覆盖用）
- Kanban 列推导逻辑（纯函数）：
  - 无 override 时：0% 掌握 -> To Learn；1-79% -> In Progress；80%+ -> Mastered
  - 有 override 时：使用 override 值，可手动清除恢复自动计算
  - 掌握度 = Mastered Concept 数 / 总 Concept 数
- GET /api/kanban：返回所有文档/课程的 Kanban 列分布 + 每项的掌握度详情
- POST /api/documents/{id}/kanban-override：设置手动覆盖
- DELETE /api/documents/{id}/kanban-override：清除覆盖恢复自动

**Kanban 前端（2 天）**
- Kanban 看板页：三列拖拽布局（To Learn / In Progress / Mastered）
- 每列展示文档/课程卡片：名称、Concept 总数、掌握度百分比、进度条
- 拖拽跨列：触发 kanban-override 设置
- 卡片点击进入文档详情 / 自适应学习
- 按 course/subject 标签筛选（过滤某科目）

**归档机制（2 天）**
- Document / Course 数据模型扩展：新增 `archived` 布尔字段 + `archived_at` 时间戳
- POST /api/documents/{id}/archive：一键归档
  - 冻结该文档所有 FSRS 闪卡的 due_date（不再推送到期复习）
  - 停止该文档的活跃突击计划
  - 从 Kanban 默认视图中隐藏（toggle 可显示已归档项）
- POST /api/documents/{id}/unarchive：取消归档
  - 恢复 FSRS 闪卡 due_date（从今天开始重新计算）
  - 恢复 Kanban 显示
  - 所有历史进度数据保留（非破坏性）
- 归档/取消归档前端：Kanban 卡片右上角菜单 + 归档视图切换

**首页仪表盘（2 天）**
- GET /api/dashboard：聚合首页数据
  - 活跃课程数 + 每课程进度条
  - 今日到期卡片数（跨所有活跃文档的 FSRS）
  - 活跃突击计划列表（倒计时 + 进度）
  - 连续学习天数（从 ReviewLog / AdaptiveSession 时间戳推导）
  - 本周学习时长（从 session timestamps 累加）
- 前端首页改造：仪表盘布局——活跃课程卡片 + 今日待办 + 突击计划 + 连续天数

### 验收标准

- [ ] Kanban 看板展示所有文档，自动按掌握度分列（To Learn / In Progress / Mastered）
- [ ] 掌握度变化时卡片自动移动到正确列（无需手动刷新）
- [ ] 可手动拖拽卡片跨列，拖拽后状态固定不再自动变化
- [ ] 可清除手动覆盖恢复自动计算
- [ ] 一键归档文档后：FSRS 闪卡不再推送、突击计划停用、Kanban 默认隐藏
- [ ] 取消归档后：所有进度恢复，FSRS 从今天重新计算到期
- [ ] 首页仪表盘显示：活跃课程数、今日到期卡片、连续学习天数、突击计划
- [ ] 可按科目标签筛选 Kanban

### 依赖

- 切片 2.1（Concept mastery_state——Kanban 列推导基于掌握度百分比）
- 切片 2.3（突击计划——归档需停用活跃计划，首页需展示突击计划）
- Phase 1 切片 1.3（FSRS 闪卡——归档需冻结/恢复闪卡调度）

---

## 切片 2.5：课程文件夹与场景标签

**目标**：yufeng 可以创建"课程"把多个文档归到一起（PPT + 教材 + 笔记），系统自动合并跨文档重复概念、生成跨文档综合题。创建课程时选择"考试"或"面试"模式，出题策略自动调整。

**用户价值**：做完这个切片后，yufeng 可以把一门课的 5 个 PPT + 1 个教材 PDF 放到一个课程文件夹里，系统自动去重概念、跨文档出综合题（PPT 的概念 + 教材的例题合成一道应用题），还能切换考试/面试模式——同一套材料先准备期末考，考完切到面试模式继续用。

**预估天数**：12 天

### 任务清单

**课程文件夹模型（2 天）**
- Course 数据模型建表：name, scene_tag(exam/interview), archived, created_at
- CourseDocument 关联表：course_id, document_id, ordering
- POST /api/courses：创建课程（name + scene_tag，默认 exam）
- POST /api/courses/{id}/documents：添加文档到课程
- DELETE /api/courses/{id}/documents/{doc_id}：从课程移除文档
- 前端课程管理页：创建课程 + 拖拽添加/移除文档 + 课程列表

**概念合并引擎（4 天）**
- CourseConcept 数据模型：merged concept at course level，links to multiple document-level Concepts via ConceptMapping
- ConceptMapping 关联表：course_concept_id, concept_id, document_id
- 文档加入课程时触发合并：
  1. 该文档已有 Phase 1 提取的 Concepts
  2. LLM 语义相似度检查：新文档 Concepts vs 课程已有 CourseConcepts
  3. 合并重复项：保留最丰富的 source_spans，链接到所有来源文档
  4. 生成统一课程级概念列表
- 合并保守原则：不确定时保持分离（false split 代价 < false merge 代价）
- POST /api/courses/{id}/merge-concepts：手动触发重新合并
- 集成测试覆盖 PRD Seam 3 全部 5 条用例（LLM mock，数据库断言）

**跨文档出题（2 天）**
- 出题引擎扩展：prompt 包含多个文档的 source material，允许综合跨文档出题
- Question 模型扩展：source_spans 从单值改为多值数组（可引用多个文档的段落）
- POST /api/courses/{id}/generate-quiz：课程级出题，跨文档综合题
- 跨文档题标注所有来源文档 + 页码，可溯源
- 移除文档时：该文档独有的 Concept 移除，共享 Concept 保留其他来源

**场景标签（2 天）**
- Course / Document scene_tag 字段（默认 exam）
- 场景配置参数（PRD 表格）：
  - Exam 模式：MCQ 40% / Fill-blank 20% / T/F 15% / Short-answer 25%，Bloom 偏 Remember/Understand/Apply
  - Interview 模式：Short-answer 40% / Open-ended 30% / MCQ 15% / Scenario 15%，Bloom 偏 Analyze/Evaluate
- PUT /api/courses/{id}/scene-tag：切换场景标签
- 切换后只影响未来出题分布，已有题目不重新生成
- 突击模式模拟考匹配场景标签的题型分布
- 前端课程创建/编辑：场景标签选择器（考试/面试）

**统一概念地图（2 天）**
- GET /api/courses/{id}/concept-map：返回课程级统一概念地图
- 前端概念地图可视化：展示跨文档概念关联，每个概念标注来源文档
- 点击概念可查看所有来源文档的相关段落
- 概念地图与掌握度状态联动（复用切片 2.1 的 mastery_state 颜色标注）

### 验收标准

- [ ] 创建课程并添加 2 个文档，系统自动提取两份文档的概念并合并去重
- [ ] 合并后的概念保留所有来源文档的 source_spans
- [ ] 添加第三个有重叠概念的文档，合并更新且不产生重复
- [ ] 移除文档后，该文档独有概念被移除，共享概念保留其他来源
- [ ] 课程级出题可生成跨文档综合题，每题标注所有来源文档和页码
- [ ] 创建课程时选择"考试"或"面试"模式，出题题型分布匹配对应配置
- [ ] 切换场景标签后，后续出题分布变化，已有题目不变
- [ ] 突击模式模拟考的题型分布匹配课程场景标签
- [ ] 概念地图展示课程级统一概念，标注来源文档和掌握度状态
- [ ] 概念合并通过集成测试（PRD Seam 3，LLM mock）

### 依赖

- 切片 2.1（Concept mastery_state——课程概念地图需展示掌握度）
- 切片 2.3（突击模式——模拟考需匹配场景标签题型分布）
- Phase 1 切片 1.1（文档解析 + Concept 提取引擎）
- Phase 1 切片 1.2（出题参数控制——场景标签修改出题分布参数）
- Phase 1 切片 1.4（DOCX 解析——课程文件夹需支持多种文档格式）

---

## 延后/砍掉的 User Stories

### 延后到 Phase 3+ 的 Stories

| Story | 内容 | 延后理由 |
|-------|------|---------|
| 8 | 自适应引擎在学习阶段混合诊断/掌握/新概念（interleaving） | 切片内降级：切片 2.1 的自适应会话按 Concept 顺序诊断，不做学习阶段交叉混合。FSRS 复习阶段本身已有交叉（Phase 1 切片 1.3 已实现）。学习阶段的 interleaving 作为增强在 Phase 3 补充——先跑通核心诊断->教学闭环更重要。 |
| 17 | 计划动态调整（提前完成则前移后续内容） | 切片内降级：切片 2.3 实现基础动态调整（Concept 状态变化触发重新规划），但"提前完成当日任务自动前移后续天数"的高级逻辑延后。先保证计划能创建、能执行、能按 Concept 状态调整即可。 |

### 切片内降级处理的 Stories

| Story | PRD 原文 | 切片内处理方式 | 理由 |
|-------|---------|--------------|------|
| 9 | 卡住后提供不同解释方式或标记手动复习 | 切片 2.1 实现 Stuck 状态 + UI 提示手动复习；"换不同解释方式"在重复教学时通过 prompt 变化实现（记录已用 prompt，要求换角度），但不做显式的"解释策略选择器" | 先跑通卡住检测 + 基础提示，高级解释策略切换后续迭代 |
| 28 | 自动检测跨文档重叠概念并合并 | 切片 2.5 用 LLM 语义相似度检查做合并；不做 embedding 向量相似度（需额外向量化基础设施）。LLM 判断够用，保守合并不确定就分离 | 向量化基础设施过重，LLM 语义判断对 yufeng 个人用量足够 |
| 32 | 统一概念地图展示跨文档概念关联 | 切片 2.5 做基础列表式概念地图（概念 + 来源文档标签 + 掌握度颜色）；不做图形化网络拓扑可视化 | 图形化网络拓扑需引入 D3/cytoscape 等可视化库，投入产出比低。列表式先够用 |

### 明确不做的（Phase 2 范围内但技术上简化）

- **学习阶段 interleaving**（Story 8）：FSRS 复习已有交叉混合（Phase 1），自适应学习阶段按 Concept 顺序诊断。学习阶段的精细 interleaving 策略延后。
- **计划自动前移**（Story 17 部分）：实现"Concept 状态变化触发重规划"，但不实现"检测到用户提前完成当日任务后自动前移"的实时监控。用户可手动触发 recalculate。
- **概念合并 embedding**（Story 28 部分）：用 LLM 语义判断替代向量相似度，不引入 embedding 基础设施。
- **图形化概念地图**（Story 32 部分）：列表式展示，不做网络拓扑图。

---

## 总工期与节奏

| 切片 | 预估天数 | 累计 |
|------|---------|------|
| 2.1 自适应引擎最小闭环 | 14 | 14 |
| 2.2 错题变体生成 | 7 | 21 |
| 2.3 考前突击模式 | 10 | 31 |
| 2.4 学习看板与归档 | 8 | 39 |
| 2.5 课程文件夹与场景标签 | 12 | 51 |

yufeng 业余时间开发，按每周 10-15 小时折算约 6-7 周可完成全部 5 个切片。切片 2.1 完成后即可体验到"系统主动诊断+教学"的核心差异化，后续切片按价值递增补充。切片 2.2 和 2.3 紧密衔接（变体强化薄弱概念 -> 突击模式调度复习），切片 2.4 提供全局视图，切片 2.5 收尾多文档和场景切换。

---

## 跨 Phase 依赖说明

| Phase 2 切片 | 依赖的 Phase 1 切片 | 依赖内容 |
|-------------|-------------------|---------|
| 2.1 自适应引擎 | 1.1, 1.2, 1.3 | 出题引擎（诊断题生成）、Concept/Question 模型、出题参数控制（按 concept/bloom/difficulty 过滤）、FSRS 间隔重复池（掌握的概念写入） |
| 2.2 错题变体 | 1.1, 1.2 | 出题引擎（变体生成）、自我批评管线（变体质量过滤）、简答评分（变体可能是简答题） |
| 2.3 考前突击 | 1.1, 1.2, 1.3 | 出题引擎（模拟考出题）、FSRS 复习（巩固阶段）、答题判分（模拟考判分） |
| 2.4 学习看板 | 1.1, 1.3 | Concept 数据模型（掌握度推导）、FSRS 闪卡（归档冻结/恢复）、ReviewLog（连续天数统计） |
| 2.5 课程文件夹 | 1.1, 1.2, 1.4 | 文档解析 + Concept 提取（多文档概念来源）、出题参数控制（场景标签修改分布）、DOCX 解析（多格式文档支持） |
