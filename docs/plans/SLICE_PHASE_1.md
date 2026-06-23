# QuizCraft Phase 1 垂直切片实施计划

> 基于 PRD_PHASE1.md + DESIGN_DECISIONS.md，按垂直切片思路拆解
> 2026-06-23

---

## 切片划分思路

### 核心原则

1. **第一条切片是最小可用闭环**：上传 PDF -> 出选择题 -> 做题 -> 错题引用文档原文解释。这是 QuizCraft 和 Quizlet/Knowt 的根本区别，也是 yufeng 自己最想用到的场景。
2. **每条切片纵向贯穿**：从前端 UI 到后端 API 到数据库到 LLM 调用，不做"先做完所有解析器"或"先做完所有题型"的横向铺层。
3. **按价值递增**：先跑通核心差异化卖点（文档出题 + 来源锚定反馈），再补完整（简答评分、闪卡、分层路由、自部署）。
4. **砍掉和延后**：Phase 1 PRD 中部分 user stories 在切片层面被延后到 Phase 2 或降级处理，详见末尾说明。

### Phase 1 PRD 的 42 条 user stories 分布

| 切片 | 覆盖 stories | 说明 |
|------|-------------|------|
| 1.1 最小出题闭环 | 1, 8, 11(部分), 12, 17, 18, 20, 21 | PDF 上传 -> 选择题 -> 做题 -> 文档引用反馈 |
| 1.2 LLM 配置与出题增强 | 9, 10, 13, 14, 16, 19, 23, 24 | LLM 设置页 + 参数控制 + 简答评分 + 交叉出题 + 预览编辑 |
| 1.3 闪卡与 FSRS 间隔重复 | 25, 26, 27, 28, 29, 30, 31, 32 | 闪卡自动生成 + FSRS 调度 + 每日复习 |
| 1.4 DOCX 支持与分层解析 | 2, 3, 4, 5, 6, 7 | DOCX 解析 + 解析进度 + L2/L3 升级 + 文档管理 |
| 1.5 自部署与离线 | 33, 34, 35, 36, 37, 38, 39, 40, 41, 42 | Docker Compose + 密码认证 + 离线模式 + 成本估算 |

---

## 切片 1.1：最小出题闭环

**目标**：yufeng 上传一份 PDF 课件，系统自动出几道选择题，做题后错题反馈引用课件原文。这是 QuizCraft 的核心差异化卖点最小化版本。

**用户价值**：做完这个切片后，yufeng 可以上传自己的课件，系统出选择题，做错后看到"你的课件第 X 页说..."的反馈——这是 Quizlet/Knowt 做不到的。

**预估天数**：12 天

### 任务清单

**后端骨架**（3 天）
- 初始化 FastAPI 项目结构（routers/models/schemas/services 分层）
- SQLite + SQLAlchemy async 数据模型建表：Document, Section, Concept, Question, QuizSession, Answer
- LLM 抽象层接口定义 + OpenAI-compatible 实现（先支持 Claude/GPT，Ollama 延后）
- LLM 配置暂用环境变量硬编码（QUIZCRAFT_LLM_PROVIDER / API_KEY / MODEL），切片 1.2 再做 UI 配置

**文档解析**（2 天）
- L1 解析器：PyMuPDF4LLM 提取 PDF 文本 + 基本结构
- 结构感知分块：按章节/标题切，512-1024 token，保留元数据（section_path, page_number）
- 上传 API：POST /api/documents（接受 PDF 文件，异步解析，存入 DB）

**出题引擎**（3 天）
- 两步生成法 Step 1：LLM 从文档分块提取 Concepts（5-10 个/块），带 source_span
- 两步生成法 Step 2：LLM 对每个 Concept 生成 2 道选择题（Bloom 记忆/理解层），每题带 source_span 引用原文
- 出题 API：POST /api/documents/{id}/generate-quiz
- 自我批评管线（简化版）：生成后 LLM 自评，淘汰低分题（只评 accuracy + source-grounding 两个维度，完整 6 维度延后）

**答题与反馈**（2 天）
- 答题 API：POST /api/quiz-sessions/{id}/answer
- 选择题即时判分（确定性）
- 反馈生成：LLM 根据用户答案 + source_span 生成引用文档原文的解释
- QuizSession 记录答题结果

**前端最小 UI**（2 天）
- Next.js 项目初始化 + App Router
- 文档上传页（拖拽上传 PDF）
- 出题按钮 + 答题界面（一题一题答，即时反馈）
- 错题反馈展示（显示引用的文档原文 + 页码）

### 验收标准

- [ ] 上传一份 PDF 课件（10-50 页），系统在 2 分钟内完成解析
- [ ] 生成 5-10 道选择题，每题显示来源页码和章节
- [ ] 选题题答完即时判分
- [ ] 错题反馈引用课件原文（如"你的课件第 12 页提到..."），而非通用解释
- [ ] 全流程通过 API 集成测试（LLM 调用 mock，SQLite 内存数据库）

### 依赖

- 无（这是第一条切片）

---

## 切片 1.2：LLM 配置与出题增强

**目标**：完善出题引擎和答题体验——用户可在 Web UI 配置 LLM、控制出题参数、预览编辑题目、简答题 LLM 评分、题目交叉排列。

**用户价值**：yufeng 可以选择用 Claude 还是 GPT、控制出题难度和题型、预览编辑生成的题目、做简答题并得到 LLM 评分。做题体验从"能用"变成"好用"。

**预估天数**：10 天

### 任务清单

**LLM 配置 UI 与后端**（2 天）
- Settings 页面：provider 选择（Claude/GPT/Gemini/Ollama）、API key 输入、model 选择、base URL（Ollama）
- LLM 配置存入 SQLite settings 表（API key 加密存储）
- POST /api/settings/llm 配置接口
- 测试调用验证：配置后发送测试请求确认连通

**出题参数控制**（2 天）
- 出题参数 API：number, difficulty_range, question_types, chapter_scope, bloom_distribution
- 前端出题配置面板（选择题数、难度、题型比例、章节范围）
- Bloom 层级完整支持：Remember/Understand/Apply/Analyze，要求 LLM 解释为什么是这个层级

**简答题生成与评分**（2 天）
- 出题引擎增加 short_answer 题型生成
- 简答题评分：LLM 按 rubric（从 source_span 派生）评分 0-1 + 引用文档反馈
- 评分 API：异步处理（LLM 评分耗时），前端轮询结果

**题目预览与编辑**（2 天）
- 出题后进入预览模式：列表展示所有题目 + 来源引用
- 用户可编辑题目文本、正确答案、干扰项
- 用户可删除不合格题目
- 确认后题目进入 practice pool

**交叉出题 + 标记坏题**（1 天）
- QuizSession 出题时按 concept 和 question_type 交叉混合，不按文档顺序
- 答题界面增加"标记坏题"按钮，标记后移出 practice pool

**完整自我批评管线**（1 天）
- 自评维度从 2 个扩展到 6 个：accuracy, clarity, difficulty, source-grounding, non-trivial, non-ambiguous
- 淘汰阈值可配（默认 <4 分淘汰）

### 验收标准

- [ ] 在 Web UI Settings 页配置 LLM provider + API key 后，测试调用成功
- [ ] 出题时可选择题型（选择题/简答题/判断题/填空题）、难度、数量、章节范围
- [ ] 简答题提交后 LLM 评分返回 0-1 分数 + 引用文档的解释
- [ ] 题目生成后可预览、编辑、删除，确认后进入练习池
- [ ] 答题时题目顺序交叉混合，不按文档章节顺序
- [ ] 可标记坏题，标记后不再出现

### 依赖

- 1.1（最小出题闭环）

---

## 切片 1.3：闪卡与 FSRS 间隔重复

**目标**：从文档概念和错题自动生成闪卡，用 FSRS 算法调度复习。错题自动变高优先级闪卡，每天推送到期复习。

**用户价值**：yufeng 做完题后，系统自动从错题和薄弱概念生成闪卡，第二天打开就能复习到期卡片。这是"间隔重复"核心卖点落地。

**预估天数**：8 天

### 任务清单

**闪卡生成**（2 天）
- 从 Concept 自动生成正反面闪卡（概念 -> 定义/解释）
- 从错题 Answer 自动生成闪卡（题目 -> 正确答案 + 文档引用）
- 错题闪卡设置 elevated priority（FSRS 初始难度更高）
- 闪卡去重：同一 Concept 不重复生成
- Flashcard 数据模型建表：front, back, concept_id, source_answer_id, FSRS 调度字段

**FSRS 调度引擎**（2 天）
- 集成 py-fsrs 后端调度
- 闪卡评分 API：POST /api/flashcards/{id}/review（rating: again/hard/good/easy）
- FSRS 参数：desired_retention 默认 0.9，daily new card limit 20，daily review limit 200
- ReviewLog 记录每次评分事件

**每日复习会话**（2 天）
- GET /api/flashcards/due：返回今日到期卡片（新卡 + 复习卡），受每日上限约束
- 复习界面：翻卡式 UI，显示正面 -> 用户回忆 -> 翻面 -> 评分（Again/Hard/Good/Easy）
- 评分后 ts-fsrs 前端即时预览下次复习时间（无需网络请求）

**闪卡管理与预测**（1 天）
- 闪卡列表页：查看所有闪卡，按状态（new/learning/review/relearning）分组
- 编辑闪卡内容（front/back 文本）
- 今日复习概览：到期数量、新卡数量、预测未来 7 天复习量

**设置项**（1 天）
- 目标记忆率设置（0.85-0.95 可选）
- 每日新卡上限、复习上限设置
- 设置存入 SQLite settings 表

### 验收标准

- [ ] 上传文档出题后，系统自动从概念和错题生成闪卡
- [ ] 错题生成的闪卡比普通闪卡更早到期（elevated priority 生效）
- [ ] 每日打开系统，显示今日到期闪卡数量
- [ ] 闪卡复习界面可翻卡、评分，评分后即时显示下次复习时间
- [ ] 可编辑闪卡内容、设置目标记忆率和每日上限
- [ ] FSRS 调度通过单元测试（py-fsrs 确定性数学，无 mock）

### 依赖

- 1.1（出题引擎产出 Concept 和 Answer）
- 1.2（简答题评分产出更多错题来源）

---

## 切片 1.4：DOCX 支持与分层解析路由

**目标**：支持 Word 文档上传，PDF 解析增加 L2/L3 分层路由，解析过程显示进度，文档可管理和重解析。

**用户价值**：yufeng 的教授可能给的是 docx 而非 PDF；复杂表格/公式的 PDF 也能正确解析；大文件解析有进度提示；可以删除和重解析文档。

**预估天数**：8 天

### 任务清单

**DOCX 解析**（2 天）
- Pandoc 集成（DOCX -> Markdown，保留结构/公式）
- Mammoth 作为 fallback（DOCX -> HTML -> Markdown）
- 上传 API 扩展支持 .docx 文件类型
- 解析结果复用切片 1.1 的分块和出题流程

**L2 结构化解析（Docling）**（2 天）
- L1 质量检测启发式：文本密度、表格标记、公式标记
- L1 质量不达标时自动升级到 L2（Docling）
- L2 处理表格、公式、多栏布局
- 保留表格/公式为原子单元，不被分块切碎

**L3 多模态 LLM 解析**（1 天）
- L2 仍不达标时升级到 L3（页面转图片送视觉 LLM）
- 仅对需要的页面调用 L3（成本控制）
- 解析结果回写到 Section 表

**解析进度与文档管理**（2 天）
- 解析进度 API：GET /api/documents/{id}/status（pending -> processing -> complete/failed）
- 前端进度条/状态指示
- 文档列表页：查看所有已上传文档、解析状态、题目/闪卡数量
- 删除文档 API：DELETE /api/documents/{id}（级联删除关联题目/闪卡）
- 重解析 API：POST /api/documents/{id}/reparse（指定解析层级）

**文档结构预览**（1 天）
- 文档详情页：展示解析后的章节结构（section_path 树形视图）
- 每个章节显示提取的 Concepts 列表
- 用户可验证系统是否正确理解了材料

### 验收标准

- [ ] 上传 .docx 文件，解析后可正常出题
- [ ] 含表格的 PDF 页面自动升级到 L2 解析，表格内容保留
- [ ] 扫描件页面自动升级到 L3，LLM 视觉解析后可出题
- [ ] 大文件解析时前端显示进度状态
- [ ] 可删除文档及其关联题目/闪卡
- [ ] 可对解析质量差的文档重新解析
- [ ] 文档详情页展示章节结构和提取的概念列表

### 依赖

- 1.1（解析流程基础）
- 1.2（LLM 配置 UI，L3 需要 LLM 视觉能力）

---

## 切片 1.5：自部署与离线模式

**目标**：一键 docker compose up 部署，密码保护，离线时可做题和复习闪卡，LLM 成本可见。

**用户价值**：yufeng 可以在自己的机器/服务器上一键部署，密码保护数据安全，断网时仍可做题和复习闪卡。

**预估天数**：6 天

### 任务清单

**Docker Compose 部署**（2 天）
- 前端 Dockerfile（Next.js standalone build）
- 后端 Dockerfile（Python + 依赖）
- docker-compose.yml：frontend + backend + shared SQLite volume
- 环境变量配置：QUIZCRAFT_PASSWORD, LLM 默认配置, DATA_DIR
- README 部署说明

**密码认证**（1 天）
- 登录页：输入密码
- 后端：环境变量 QUIZCRAFT_PASSWORD 校验，签发 httpOnly session cookie（JWT）
- 中间件：所有 API 端点需认证（除 /api/auth/login）
- 前端：cookie 自动携带，刷新浏览器保持登录

**离线模式**（2 天）
- 前端缓存策略：活跃 quiz session + 到期闪卡本地缓存（IndexedDB / localStorage）
- 离线检测：网络断开时 UI 提示"离线模式"
- 离线可做：客观题判分（本地）、闪卡复习（FSRS 本地计算）
- 离线不可做：出新题、简答评分（提示"需联网"）
- 重连后：pending 简答评分批量提交

**LLM 成本估算**（1 天）
- 每次 LLM 调用记录 token 用量 + 估算成本
- Settings 页展示累计成本 + 按操作类型拆分
- 出题/解析前显示预估成本

### 验收标准

- [ ] `docker compose up` 一条命令启动前后端，浏览器可访问
- [ ] 未登录访问任何页面跳转登录页
- [ ] 输入正确密码后登录，刷新浏览器保持登录态
- [ ] 断网后可继续做题（客观题）和复习闪卡
- [ ] 断网时出新题/简答评分提示"需联网"
- [ ] 重连后离线期间的评分请求自动补提交
- [ ] Settings 页显示 LLM 累计成本

### 依赖

- 1.1（核心功能）
- 1.2（LLM 配置）
- 1.3（闪卡复习，离线核心场景）
- 1.4（文档解析，完整功能集）

---

## 延后/砍掉的 User Stories

### 延后到 Phase 2

| Story | 内容 | 延后理由 |
|-------|------|---------|
| 4 | 保留表格/公式/图片 | 切片 1.1 用 L1 解析只处理文本，表格/公式在切片 1.4 的 L2/L3 才完整支持。但 1.4 已经覆盖了——不算延后，确认归入 1.4。 |

**修正**：重新检查后，所有 42 条 stories 在 5 个切片中都有归属，没有被延后到 Phase 2 的。以下是对部分 stories 的降级处理说明：

### 切片内降级处理的 Stories

| Story | PRD 原文 | 切片内处理方式 | 理由 |
|-------|---------|--------------|------|
| 11 | 混合题型（选择/填空/判断/简答） | 切片 1.1 只做选择题；判断题/填空题在 1.2 补；简答题在 1.2 补 | 选择题是最快跑通闭环的题型，判断/填空/简答依赖参数控制和简答评分，放 1.2 |
| 13 | MCQ 干扰项基于常见误解 | 切片 1.1 简化版（LLM prompt 要求基于误解但不强制验证）；1.2 完整版（自评维度 + 干扰项解释） | 先跑通再说，完整质量控制在 1.2 |
| 39 | LLM 成本估算 | 切片 1.5 才做 | 前期 yufeng 自己测试用量不大，成本可见性在自部署时才有价值 |

### 明确不做的（Phase 1 范围内但技术上简化）

- **判断题**：技术上和选择题几乎一样（2 选项的选择题），在 1.2 实现时作为选择题特例处理，不单独开发。
- **填空题**：评分逻辑和选择题类似（精确匹配/模糊匹配），在 1.2 实现。
- **离线缓存深度**：Phase 1 只缓存当前活跃 session + 到期闪卡。不缓存全部历史数据。完整离线 PWA 在后续迭代。

---

## 总工期与节奏

| 切片 | 预估天数 | 累计 |
|------|---------|------|
| 1.1 最小出题闭环 | 12 | 12 |
| 1.2 LLM 配置与出题增强 | 10 | 22 |
| 1.3 闪卡与 FSRS 间隔重复 | 8 | 30 |
| 1.4 DOCX 支持与分层解析路由 | 8 | 38 |
| 1.5 自部署与离线模式 | 6 | 44 |

yufeng 业余时间开发，按每周 10-15 小时折算约 5-6 周可完成全部 5 个切片。切片 1.1 完成后即可自己用起来，后续切片按价值递增补充。
