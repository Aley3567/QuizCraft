# QuizCraft Phase 3 垂直切片实施计划

> 基于 PRD_PHASE3.md + DESIGN_DECISIONS.md，按垂直切片思路拆解
> 2026-06-23 | 依赖 Phase 1 全部 5 个切片 + Phase 2 切片 2.1/2.3/2.4

---

## 切片划分思路

### 核心原则

1. **第一条切片是最小可用闭环**：手写一道预置实操题 → 启动安全沙箱容器 → xterm.js 连接终端 → 用户敲命令 → 点 Check 跑 check.sh → pass/fail 反馈。这是 Phase 3 区别于 Phase 1/2 的根本卖点——从"我能答对理论题"到"我能在真终端里把事做成"的最小化版本。Docker 沙箱是最大风险点，安全护栏在第一条切片就立住，不延后。
2. **每条切片纵向贯穿**：从前端 xterm.js UI 到 WebSocket 到 FastAPI 到 Docker 沙箱到 check.sh 执行一条龙打通，不做"先做完所有沙箱管理"或"先做完所有题生成器"的横向铺层。
3. **按价值递增**：端到端闭环（3.1）-> 终端体验+多步验证（3.2）-> 实操题自动生成（3.3）-> 理论-实践联动（3.4）-> 挑战目录与管理（3.5）。先跑通"能让人惊叹"的差异化路径，再补完整体验、自动生成、联动、管理。
4. **安全护栏不降级**：unprivileged、no-new-privileges、--network none、cgroups 资源限制、TTL 强制清理、no host mounts、check.sh 非 root——全部在切片 3.1 立住，后续切片只在此基础上扩展。
5. **跨 Phase 依赖**：所有切片依赖 Phase 1 切片 1.1（文档解析、Concept/Question 模型）+ 1.2（LLM 抽象层、出题引擎）。切片 3.3 额外依赖 1.1 文档分块和 Concept 提取。切片 3.4 依赖 Phase 2 切片 2.1（自适应状态机、mastery_state）、2.3（考前突击 planner）、2.4（Kanban 看板、归档）。

### Phase 3 PRD 的 54 条 user stories 分布

| 切片 | 覆盖 stories | 说明 |
|------|-------------|------|
| 3.1 沙箱+终端+验证最小闭环 | 1, 2, 3, 4, 5, 7, 8, 10, 11, 13, 17, 19, 27, 28, 29, 30, 32 | 沙箱生命周期+安全护栏+xterm.js+check.sh 验证引擎+手写预置题端到端跑通 |
| 3.2 终端体验完善+多步验证 | 6, 12, 14, 15, 16, 18, 22, 23, 24, 25, 26, 31, 34 | 多步 challenge+部分进度+渐进提示+终端 UX 完善+TTL 警告 |
| 3.3 实操题自动生成管线 | 33, 35, 36, 37, 38, 39, 40, 41 | LLM 从教材生成 challenge bundle+自动质量门+人工审核 gate+多难度+LLM 验证 fallback |
| 3.4 理论-实践联动 | 42, 43, 44, 45, 46, 47 | Concept 关联+mastery 更新+交叉推荐+FSRS 联动+Cram/Kanban 集成 |
| 3.5 挑战目录与管理 | 9, 20, 21, 48, 49, 50, 51, 52, 53, 54 | Catalog 浏览筛选+多镜像+历史+重做+自定义+导入导出+收藏+统计 |

---

## 切片 3.1：沙箱+终端+验证最小闭环

**目标**：yufeng 打开一道手写预置的实操题（如"用 grep 找出 /etc 下所有包含 error 的行"），系统自动启动一个安全隔离的 Docker 容器，xterm.js 终端连上，用户敲命令操作，点 Check 按钮在容器内跑 check.sh，exit 0 显示通过、非 0 显示提示。这是 Phase 3 核心差异化卖点的最小化版本，也是最大风险点（Docker 沙箱+WebSocket 终端）首次落地。

**用户价值**：做完这个切片后，yufeng 第一次在浏览器里拥有一个真实的 Linux 终端环境，能动手练命令、点 Check 拿到确定性反馈——这是 Phase 1/2 的理论题给不了的肌肉记忆训练。安全护栏全开，不用担心容器逃逸或资源耗尽炸掉自己的机器。

**预估天数**：16 天

### 任务清单

**Docker 沙箱生命周期管理（4 天）**
- 集成 docker-py SDK，封装 `SandboxManager` 服务层（创建/销毁/重置/查询状态）
- 容器创建参数固化安全基线（不可降级）：
  - unprivileged + `--security-opt=no-new-privileges`
  - `--network none`（默认无网络）
  - 资源限制：`--memory=256m`、`--cpus=0.5`、`--pids-limit=100`（按 challenge 可配，但下限不可为空）
  - 不挂载 host volume（challenge 文件在 setup.sh 阶段 `docker cp` 进去，不 bind-mount）
- 容器状态机：`creating` → `running` → `stopped` → `destroyed`，禁止非法转换（如 `destroyed → running`）
- `ContainerSession` 数据模型建表：id, attempt_id, container_docker_id, image, status, created_at, destroyed_at, destroy_reason(completed/timeout/reset/cleanup)
- TTL 强制销毁：每 challenge 默认 30 分钟，后端 asyncio 定时器 + 独立 cleanup daemon 每 60s 扫描 orphaned 容器并销毁
- 重置功能：一键销毁旧容器+创建同配置新容器（Story 3）
- 部署架构：Docker-outside-of-Docker，host 的 `/var/run/docker.sock` 挂入 backend 容器，sibling 容器跑在独立 Docker 网络上

**check.sh 验证引擎（2 天）**
- `VerificationEngine` 服务：接收 check 请求 → `docker exec` 在容器内执行 `check.sh`（或 `check.sh {step}`）→ 解析 exit code + stdout
- exit code 约定：0=通过、1=失败（stdout 作提示）、2=环境错误（check.sh 本身 bug，UI 区分展示）、124=超时
- 10 秒超时（可配），超时视为失败+"验证超时"提示
- stdout 二进制/garbage 容错：截断或 sanitize 后存储
- `ChallengeCheck` 数据模型建表：id, attempt_id, step_number, passed, hint_message, executed_at
- 单元测试覆盖 PRD Seam 2 全部 9 条用例（docker exec mock，纯逻辑验证解析+超时+状态记录）

**xterm.js + WebSocket 终端（4 天）**
- FastAPI WebSocket endpoint `/ws/terminal/{attempt_id}`：接收前端 binary frames，relay 到 `docker exec -it` 的 stdin，反向 relay stdout 到前端
- 用 docker-py 的 `exec_create` + `exec_start` with TTY=True，asyncio stream 双向 pump
- xterm.js 前端组件：fit addon 自适应尺寸、WebLinks addon、search addon
- SIGWINCH 处理：前端 resize 时通过 WebSocket 发送 resize 消息，后端调用 `exec_resize` 调整 PTY winsize
- 基础键盘快捷键支持（Ctrl+C/D/Z、tab 补全由容器内 shell 提供）
- WebSocket 断线检测 + 自动重连：断线后容器保留，重连在 TTL 内复用同一容器（exec session 一次性，重连后新建 exec）
- 后端 `TerminalRelay` 会话管理：attempt_id → 活跃 exec session 映射

**数据模型与 challenge bundle 存储（2 天）**
- `TerminalChallenge` 数据模型建表：id, title, description, difficulty, topic, base_image, time_limit_seconds, network_mode, verification_mode, step_count, concept_id(FK, 可空), section_id(FK, 可空), source_span, status(draft/review/published), bundle_path, created_at, updated_at
- `ChallengeAttempt` 数据模型建表：id, challenge_id, started_at, ended_at, status(in_progress/passed/failed/timed_out/abandoned), steps_completed, total_checks, container_id
- challenge bundle 文件系统结构：`data/challenges/{challenge_id}/{meta.yaml, instructions.md, setup.sh, check.sh, solve.sh, cleanup.sh}`
- meta.yaml 解析器（PyYAML）：加载 challenge 元数据进 SQLite 索引
- setup.sh 在容器创建后执行：`docker cp` bundle 目录进容器 → `docker exec` 运行 setup.sh 配置场景（创建文件/用户/装包）
- 手写一道预置 challenge（如 grep 实操题）：完整 bundle + 经验证的 check.sh，作为第一条切片的验收载体和后续生成的黄金样例

**前端 split-pane UI（2 天）**
- 挑战页布局：左侧 instructions.md 渲染（react-markdown）+ 右侧 xterm.js 终端
- 顶部状态栏：容器状态指示（creating/running/stopped/timed out）+ 剩余时间倒计时 + 重置按钮 + Check 按钮
- Check 按钮点击 → 调用验证 API → 展示 pass/fail 结果卡片（含 hint message）
- challenge 列表入口（最简：列出 published 状态的 challenge，点击进入）
- Next.js App Router 路由：`/challenges` 列表、`/challenges/[id]` 详情+终端

**端到端集成与测试（2 天）**
- 真实 Docker daemon 集成测试（标记 `@pytest.mark.integration`，CI 可选跳过）：启动容器→setup.sh→模拟用户输入→check.sh→销毁全流程
- Sandbox 生命周期单元测试覆盖 PRD Seam 1 全部 8 条用例（docker-py mock：验证 container_create 参数、状态转换、TTL 销毁、cleanup sweep、WebSocket 重连复用、资源限制传递）
- 性能预算验证：容器冷启动 < 2s、WebSocket 连接 < 500ms、check.sh < 5s

### 验收标准

- [ ] 打开一道预置实操题，点击开始，3 秒内容器进入 running 状态，xterm.js 显示可交互终端
- [ ] 在终端里能正常敲命令、看到输出、Ctrl+C 中断、tab 补全
- [ ] 调整浏览器窗口大小，终端内容正确重排（vim/htop 等 TUI 不乱）
- [ ] 点 Check 按钮，5 秒内返回 pass/fail；失败时显示 check.sh stdout 作为提示
- [ ] 点重置按钮，旧容器销毁、新容器创建，环境回到 setup.sh 后的初始状态
- [ ] 容器超过 TTL（测试用短 TTL）自动销毁，destroy_reason=timeout
- [ ] 容器以 unprivileged + no-new-privileges + --network none + 资源限制启动（可 docker inspect 验证）
- [ ] cleanup daemon 扫描时只销毁超 TTL 的 orphaned 容器，不误杀活跃容器
- [ ] 关闭浏览器标签再重开，TTL 内重连复用同一容器（不新建容器）
- [ ] 沙箱生命周期管理通过单元测试（PRD Seam 1，8 条用例，docker-py mock）
- [ ] 验证引擎通过单元测试（PRD Seam 2，9 条用例，docker exec mock）

### 依赖

- Phase 1 切片 1.1（FastAPI 项目骨架、数据模型分层、LLM 抽象层接口——本切片不直接调 LLM，但复用项目结构）
- Phase 1 切片 1.5（Docker Compose 部署——沙箱需要 host docker.sock 挂载配置）

---

## 切片 3.2：终端体验完善+多步验证

**目标**：完善终端体验和挑战内容模型——支持多步 challenge（check.sh 接 step 参数，部分进度可见）、渐进提示系统（失败后渐进给提示，两次失败后可看解答）、终端 UX 完善（复制粘贴、reconnect、scrollback、字号、面板折叠）、TTL 到期前 5 分钟警告。

**用户价值**：做完这个切片后，yufeng 的终端体验从"能用"变成"好用"——像在自己机器上开终端一样顺手，多步任务有增量反馈不会做到一半不知道对不对，卡住了有渐进提示不会直接看答案。这是支撑长时间练习的体验基础。

**预估天数**：8 天

### 任务清单

**多步 challenge 与部分进度（2 天）**
- meta.yaml 扩展 `step_count` + `steps[]`（每步 description）
- check.sh 支持 step 参数：`docker exec ... check.sh {step}`，验证引擎解析 step_number
- 部分进度跟踪：ChallengeAttempt.steps_completed 更新，UI 显示"3/5 步已完成"
- 前端多步进度条：每步一个节点，通过/未通过/未检查三态着色

**渐进提示系统（2 天）**
- instructions.md 支持 collapsible hint block（markdown 扩展语法，如 `??? hint "提示 1"`）
- 提示分级：第一级模糊、第二级具体、第三级接近答案
- 前端提示抽屉：失败后解锁下一级提示，记录已查看提示级别
- "显示解答"按钮：ChallengeAttempt.total_checks >= 2 次失败后解锁，展示 solve.sh 内容
- 提示查看记录存 ChallengeCheck 或新表 HintView

**终端 UX 完善（2 天）**
- 复制粘贴：xterm.js 右键粘贴 + Ctrl+Shift+C/V 快捷键（需处理浏览器安全策略）
- scrollback：配置 xterm.js scrollback 行数（默认 1000），会话内保留历史
- 字号调整：+/- 按钮或设置项，持久化到 localStorage
- instruction panel 折叠：左侧面板可全宽终端或全宽说明，记忆用户偏好
- WebSocket reconnect：断线后前端自动重连，重连期间终端显示"重连中..."状态，重连后恢复 scrollback

**TTL 警告与命令历史（1 天）**
- TTL 到期前 5 分钟通过 WebSocket 推送 warning 消息，前端弹非阻塞提示"剩余 5 分钟"
- 命令历史采集：容器内 `~/.bash_history` 读取，失败后可选展示历史命令供回顾（Story 34 基础版：仅展示，不做智能错误定位）

**前端整合（1 天）**
- 多步+提示+UX 组件整合到挑战详情页
- 预置第二道多步 challenge（如"配置一个 nginx 虚拟主机"3 步题）作为验收载体

### 验收标准

- [ ] 多步 challenge 每步可单独 Check，部分进度实时可见（如 2/3）
- [ ] 失败后可查看渐进提示，每级提示内容递进具体
- [ ] 连续 2 次 Check 失败后"显示解答"按钮解锁
- [ ] 终端支持右键粘贴、Ctrl+Shift+C/V 复制粘贴
- [ ] 终端字号可调，调整后持久化
- [ ] 左侧说明面板可折叠为全宽终端或全宽说明
- [ ] WebSocket 短暂断线后自动重连，终端恢复可交互
- [ ] TTL 到期前 5 分钟收到非阻塞警告
- [ ] 失败后可查看容器内命令历史（基础展示）

### 依赖

- 切片 3.1（沙箱生命周期、验证引擎、xterm.js 终端、数据模型）

---

## 切片 3.3：实操题自动生成管线

**目标**：yufeng 上传 Linux 教材，系统对包含实操概念的章节自动生成 challenge bundle（meta + instructions + setup.sh + check.sh + solve.sh），经过自动质量门检查后进入"待审核"队列，yufeng 预览、可在沙箱里试跑、编辑修正后发布。同一概念可生成多难度级别的挑战。

**用户价值**：做完这个切片后，yufeng 不再需要手写实操题——上传 Linux 课件，系统自动产出配套的动手练习，练的正是刚学的概念。人工审核 gate 保证质量，避免 LLM 生成的烂题/错题误导学习。

**预估天数**：10 天

### 任务清单

**LLM 生成管线（3 天）**
- 生成 prompt 工程：输入 = 文档 section 文本 + Concept + source_span；输出 = 结构化 JSON（meta 字段 + instructions.md + setup.sh + check.sh + solve.sh 内容）
- few-shot 示例：2-3 个手写的黄金 challenge 样例（切片 3.1 预置题复用）
- prompt 约束：
  - check.sh 测试最终状态而非具体命令（允许多种解法）
  - setup.sh 创建真实场景而非空白环境
  - check.sh 用正确 exit code（0/1/2）
  - instructions.md 含任务描述+预期结果+约束
- LLM 调用复用 Phase 1 LLM 抽象层，异步生成（10-30s 可接受）
- 生成 API：POST /api/documents/{id}/sections/{sid}/generate-challenge
- LLM verification fallback（Story 33 简化版）：challenge 标记 `verification_mode: llm` 时，验证引擎采集容器状态+命令历史，LLM 按 rubric 判 pass/fail，opt-in 非默认

**自动质量门（2 天）**
- 生成后自动检查脚本：
  - check.sh 是否使用正确 exit code（含 `exit 0` / `exit 1` 模式）
  - setup.sh 是否含危险操作（`rm -rf /`、`dd if=`、`mkfs`、`:(){ :|:& };:` fork bomb 等黑名单）
  - instructions.md 是否非空且连贯
  - 难度是否匹配源 Concept 复杂度
- 质量门不通过的 challenge 标记 quality_issues，仍进 review 队列但高亮问题
- 质量门逻辑可单元测试（确定性，无 LLM）

**人工审核 gate（2 天）**
- 生成 challenge 默认 status=review，不进 practice pool
- 审核 UI：预览 instructions.md 渲染 + 查看 setup.sh/check.sh 源码（语法高亮）
- "在沙箱试跑"流程：一键启动容器→跑 setup.sh→按说明操作→跑 check.sh 验证→确认通过后发布
- 编辑功能：可修改任意文件（instructions/setup/check/solve）后保存
- 发布/拒绝/重生成操作：发布后 status=published 进 practice pool；拒绝后可调重生成（新 LLM 调用）
- challenge 与 Concept + Section 关联记录（concept_id, section_id, source_span）

**多难度生成（2 天）**
- 同一 Concept 生成 beginner/intermediate/advanced 三级：
  - beginner：单命令、说明清晰、最小上下文
  - intermediate：2-5 命令、需读 man page 或组合工具
  - advanced：多步工作流、调试损坏状态、脚本编写
- 生成 API 支持指定 difficulty 或一次生成多难度
- 概念-挑战关联视图：某 Concept 下所有挑战列表+难度分布
- 集成测试覆盖 PRD Seam 3 全部 7 条用例（LLM mock：fixture section→生成→质量门→review→发布/拒绝/重生成→无实操概念的处理→多难度）

**纯理论章节处理（1 天）**
- 生成前判断 section 是否含实操概念（如纯 OS 历史不生成）
- 无实操概念时：不生成或生成低置信度结果标记 review
- 复用 Phase 1 切片 1.2 的 Concept Bloom 层级判断（Apply 以下不生成实操题）

### 验收标准

- [ ] 上传 Linux 教材后，对含实操概念的章节自动生成 challenge bundle（含 meta/instructions/setup/check/solve）
- [ ] 生成的 challenge 引用源 section 和页码（source_span 可溯源）
- [ ] 自动质量门能检出：check.sh 缺 exit code、setup.sh 含危险命令、空 instructions
- [ ] 生成的 challenge 默认 status=review，不进 practice pool
- [ ] 审核界面可预览说明、查看脚本源码、在沙箱试跑验证
- [ ] 可编辑任意文件后发布，发布后进 practice pool
- [ ] 拒绝后可重新生成（新 LLM 调用）
- [ ] 同一 Concept 可生成 beginner/intermediate/advanced 三级挑战
- [ ] 纯理论章节不生成或标记低置信度
- [ ] LLM verification fallback 在 opt-in challenge 上工作（mock LLM 返回 pass/fail）
- [ ] 生成管线通过集成测试（PRD Seam 3，7 条用例，LLM mock）

### 依赖

- 切片 3.1（沙箱、验证引擎、数据模型、challenge bundle 存储）
- Phase 1 切片 1.1（文档解析、Section/Concept 提取、source_span）
- Phase 1 切片 1.2（LLM 抽象层、出题 prompt 工程、自我批评管线可复用思路）

---

## 切片 3.4：理论-实践联动

**目标**：TerminalChallenge 与 Phase 1/2 的 Concept 打通——完成实操题更新 mastery 状态、FSRS 调度；理论题答错推荐对应实操题；实操题反复失败推荐回去看理论；突击计划纳入实操题；Kanban 统一展示。这是 Phase 3 与 Phase 1/2 衔接的核心价值。

**用户价值**：做完这个切片后，yufeng 的学习和练习不再是两套系统——理论题做错直接推荐动手练，动手练通了理论掌握度也跟着涨，突击计划里既有理论复习也有实操训练，看板上一眼看到全貌。理论和实践互相强化。

**预估天数**：8 天

### 任务清单

**Concept 关联与 mastery 联动（3 天）**
- TerminalChallenge.concept_id FK 到 Concept（Phase 1/2 同一实体）落地
- 挑战完成（所有 step passed）触发 mastery 信号：等价于 Phase 2 自适应引擎答对诊断题
  - Concept 在 Teaching 状态 → 完成挑战可推进到 Mastered
  - Concept 已 Mastered（纯理论）→ 完成挑战作为实践强化信号
  - Concept 在 Unknown/Diagnosing → 完成挑战标记为已掌握实践维度
- 复用 Phase 2 切片 2.1 的状态机转换逻辑（纯函数），新增 trigger_event=challenge_completed
- ChallengeAttempt 完成时调用 mastery 更新服务，写 MasteryTransition 日志
- FSRS 联动：成功完成挑战 = 对关联 Flashcard 的一次 Good review，更新 FSRS 调度
- 单元测试：状态机新增 challenge_completed 触发路径全覆盖（确定性，无 LLM/Docker）

**交叉推荐（2 天）**
- 理论题答错→推荐实操：Answer 错误 + 关联 Concept 有 published TerminalChallenge → 答题反馈区显示"动手练这道题"链接
- 实操题反复失败→推荐理论：ChallengeAttempt 同一 challenge 连续失败 >= 2 次 → UI 显示"回去看看理论"链接（指向 Concept 的 source_span 文档段落）
- 推荐数据 API：GET /api/concepts/{id}/related-challenges、GET /api/challenges/{id}/related-theory
- 前端推荐卡片组件（复用于答题反馈页和挑战失败页）

**Cram 模式集成（1 天）**
- Phase 2 切片 2.3 的 StudyPlan planner 扩展：practical 类型的 Concept 在计划中生成 terminal-challenge 类型的 PlanTask
- Cram dashboard 今日任务展示 terminal-challenge 任务（与 diagnostic/teaching/review 并列）
- 模拟考阶段可包含实操题（如果课程有 published 实操题）

**Kanban 统一视图（1 天）**
- Phase 2 切片 2.4 的 Kanban 卡片增加实操进度：挑战完成数/总挑战数
- 首页 dashboard 增加 terminal challenge 统计（今日完成数、连续天数合并计算）
- 归档文档时连带冻结关联 challenge 的推荐（不删除历史 attempt）

**测试（1 天）**
- 联动集成测试：完成挑战→mastery 更新→FSRS 调度变化→Kanban 列移动 全链路（Docker mock，状态机真实）
- 交叉推荐逻辑测试

### 验收标准

- [ ] 完成一道实操题后，关联 Concept 的 mastery 状态更新（Teaching→Mastered 或已 Mastered 的强化）
- [ ] 完成实操题触发关联 Flashcard 的 FSRS Good review，下次复习时间更新
- [ ] 理论题答错且该 Concept 有实操题时，反馈区显示"动手练这道题"链接
- [ ] 实操题连续失败 2 次后，UI 显示"回去看理论"链接（指向文档段落）
- [ ] 突击计划中 practical Concept 生成 terminal-challenge 任务，看板可见
- [ ] Kanban 卡片展示实操进度，首页 dashboard 合并统计
- [ ] 归档文档不影响历史 attempt 但停止新推荐
- [ ] 联动逻辑通过集成测试（状态机真实，Docker mock）

### 依赖

- 切片 3.1（TerminalChallenge/ChallengeAttempt 数据模型）
- 切片 3.3（自动生成的 challenge 需 concept_id 关联——手动预置题也可关联，但自动生成是主要来源）
- Phase 1 切片 1.1（Concept/Question/Answer 模型、source_span）
- Phase 1 切片 1.3（FSRS 间隔重复池、Flashcard 调度）
- Phase 2 切片 2.1（自适应状态机、mastery_state、MasteryTransition）
- Phase 2 切片 2.3（StudyPlan planner、PlanTask）
- Phase 2 切片 2.4（Kanban 看板、dashboard、归档）

---

## 切片 3.5：挑战目录与管理

**目标**：完整的挑战管理体验——Catalog 浏览筛选（topic/difficulty/完成状态）、attempt 历史、重做已通过挑战、手动创建自定义 challenge、导入导出、收藏、dashboard 统计、多镜像支持。

**用户价值**：做完这个切片后，yufeng 有一个完整的实操练习库——能按主题难度找题、看历史进步、重做练肌肉记忆、自己加题、备份分享、收藏好题、dashboard 看练习统计。从"能跑通一道题"到"有一套可持续练习的系统"。

**预估天数**：8 天

### 任务清单

**Catalog 浏览与多镜像（2 天）**
- GET /api/challenges：分页+筛选（topic, difficulty, completion_status, favorited）
- Catalog 前端页：卡片网格，筛选侧栏（主题/难度/状态多选），搜索框
- 多镜像支持（Story 9）：base_image 在 meta.yaml 声明，SandboxManager 按声明选镜像
- 预构建镜像：仅预构建 `quizcraft/sandbox:ubuntu`（默认，docker-compose build 时构建）；alpine/centos 的 Dockerfile 留仓库内按需 `docker build`，不在部署时强制构建

**Attempt 历史与重做（1 天）**
- GET /api/challenges/{id}/attempts：历史 attempt 列表（时间、状态、耗时、检查次数）
- 重做已通过 challenge：新建 attempt，不影响历史记录，用于肌肉记忆训练
- 前端 challenge 详情页展示历史 attempt 时间线

**自定义 challenge 创建（2 天）**
- 手动创建 API：POST /api/challenges（手动上传/编写 meta + instructions + setup.sh + check.sh + solve.sh）
- 自定义 challenge 编辑器 UI：表单 + 代码编辑器（CodeMirror/Monaco 轻量版）
- "在沙箱试跑"复用切片 3.3 的试跑流程
- 自定义 challenge 默认 status=published（用户自建不需要审核 gate，但提供试跑）

**导入导出（1 天）**
- 导出：challenge bundle 打包为 zip（含 meta.yaml + 脚本 + instructions）
- 导入：上传 zip，解析校验后存入 `data/challenges/`，status=draft（导入需确认发布）
- 格式规范文档化（JSON/YAML + 脚本目录结构）

**收藏与统计（1 天）**
- TerminalChallenge 增加 favorited 字段或独立 Bookmark 表
- POST /api/challenges/{id}/favorite、DELETE 取消
- Catalog 支持按收藏筛选
- Dashboard 统计 API：总完成数、通过率、平均耗时、当前连续天数、按 topic 分布
- 首页 dashboard terminal challenge 卡片（与 Phase 2 dashboard 合并）

**整理与测试（1 天）**
- Catalog 端到端测试
- 多镜像启动测试（alpine/centos challenge 能正确启动+check）

### 验收标准

- [ ] Catalog 页按主题、难度、完成状态筛选挑战
- [ ] 默认支持 ubuntu 镜像；meta.yaml 声明其他镜像（alpine/centos）时按需 build 后可启动（非部署强制项）
- [ ] 查看某 challenge 的历史 attempt（时间、状态、耗时）
- [ ] 可重做已通过 challenge，新建 attempt 不影响历史
- [ ] 手动创建自定义 challenge（编写 meta+instructions+脚本），试跑后发布
- [ ] 导出 challenge 为 zip，导入 zip 后恢复 challenge
- [ ] 可收藏 challenge，Catalog 按收藏筛选
- [ ] Dashboard 展示 terminal challenge 统计（完成数、通过率、连续天数）

### 依赖

- 切片 3.1（challenge 数据模型、沙箱、bundle 存储）
- 切片 3.2（多步 challenge、提示系统——自定义 challenge 可用多步）
- 切片 3.4（Concept 关联——Catalog 可按关联概念筛选）
- Phase 2 切片 2.4（dashboard 统一视图）

---

## 延后/砍掉的 User Stories

### 延后到 Phase 4+ 的 Stories

| Story | 内容 | 延后理由 |
|-------|------|---------|
| 52（部分）| 导入导出挑战为分享格式 | 切片 3.5 实现基础导入导出（本地备份）；"分享"（挑战市场/社区）属 Phase 4 生态，需用户系统支持。本地备份足够个人使用。 |
| 多用户沙箱隔离 | PRD 已明确 out of scope | 单用户自部署不需要，Phase 4 多用户时再考虑 namespace 隔离+配额。 |
| Firecracker/gVisor 强隔离 | PRD 已明确 out of scope | 多租户才需要，Docker 默认隔离对单用户足够。 |

### 切片内降级处理的 Stories

| Story | PRD 原文 | 切片内处理方式 | 理由 |
|-------|---------|--------------|------|
| 33 | LLM verification fallback | 切片 3.3 实现简化版：opt-in per challenge，采集容器状态+命令历史送 LLM 判 pass/fail；不做 rubric 细粒度评分，不做 LLM 判断质量自评。check.sh 仍是默认且优先。 | LLM verification 是兜底不是主路径，先保证脚本验证可靠。完整 rubric 评分后续迭代。 |
| 34 | 失败后命令历史回顾 | 切片 3.2 实现基础版：展示 ~/.bash_history 命令列表；不做"系统智能指出哪里出错"的错误定位。 | 智能错误定位需 LLM 分析命令序列，复杂度高且效果不确定。先给原始历史供用户自查。 |
| 9 | 多镜像支持 | 切片 3.5 才做（ubuntu/alpine/centos）；切片 3.1 只用默认 ubuntu 镜像跑通闭环。 | 第一条切片聚焦端到端闭环，多镜像属于完善体验，不阻塞核心路径。 |
| 14 | WebSocket 自动重连 | 切片 3.1 实现基础重连（断线后 TTL 内复用容器，新建 exec）；切片 3.2 完善为前端自动重连+状态提示。 | 3.1 保证不断线丢容器，3.2 补前端体验。 |
| 6 | TTL 到期前 5 分钟警告 | 切片 3.1 实现后端 TTL 销毁；切片 3.2 补前端 5 分钟警告推送。 | 销毁是安全底线必须先做，警告是体验增强可后补。 |
| 20, 21 | 按难度/主题组织 | 切片 3.5 Catalog 实现；切片 3.1 仅按列表展示 published challenge。 | 组织筛选属管理体验，先跑通单题闭环。 |

### 明确不做的（Phase 3 范围内但技术上简化）

- **check.sh 的 LLM 自评**：生成 check.sh 后不做"LLM 验证 check.sh 逻辑正确性"的二次自评（类似 Phase 1 自我批评管线），只做规则化质量门（exit code 模式、危险命令黑名单）。LLM 自评 check.sh 逻辑投入产出比低，人工审核 gate 已能兜底。
- **挑战难度自适应推荐**：不做"根据用户当前水平自动推荐合适难度挑战"的推荐算法。Catalog 筛选+交叉推荐（切片 3.4）已够用。自适应推荐延后。
- **容器内 session 持久化（tmux/screen）**：PRD 说重连后若 exec session gone 则新建 exec，但新建 exec 会丢失容器内 shell 状态（cwd、history、后台进程）。切片 3.1 接受这一限制（重连后新建 exec，状态丢失），不引入 tmux 持久化。若 yufeng 重连丢状态体验不可接受，作为增强在后续迭代引入 tmux wrapper。

---

## 总工期与节奏

| 切片 | 预估天数 | 累计 |
|------|---------|------|
| 3.1 沙箱+终端+验证最小闭环 | 16 | 16 |
| 3.2 终端体验完善+多步验证 | 8 | 24 |
| 3.3 实操题自动生成管线 | 10 | 34 |
| 3.4 理论-实践联动 | 8 | 42 |
| 3.5 挑战目录与管理 | 8 | 50 |

yufeng 业余时间开发，按每周 10-15 小时折算约 6-7 周可完成全部 5 个切片。切片 3.1 是最重也最关键的切片（Docker 沙箱+WebSocket+xterm.js 全新基础设施+安全护栏），完成后即可体验到"浏览器里真实终端练命令"的核心差异化，后续切片按价值递增补充。切片 3.3 依赖 3.1 的沙箱和验证引擎，切片 3.4 依赖 3.3 生成 challenge 的 concept 关联（手动预置题也可关联，但自动生成是主要来源），切片 3.5 是收尾管理体验。

---

## 跨 Phase 依赖说明

| Phase 3 切片 | 依赖的 Phase 1/2 切片 | 依赖内容 |
|-------------|---------------------|---------|
| 3.1 沙箱+终端+验证 | 1.1, 1.5 | FastAPI 项目骨架+数据模型分层、Docker Compose 部署（docker.sock 挂载配置） |
| 3.2 终端体验+多步 | 3.1 | 沙箱生命周期、验证引擎、xterm.js 终端、数据模型 |
| 3.3 实操题自动生成 | 1.1, 1.2, 3.1 | 文档解析+Section/Concept+source_span、LLM 抽象层+prompt 工程、沙箱+验证引擎+bundle 存储 |
| 3.4 理论-实践联动 | 1.1, 1.3, 2.1, 2.3, 2.4, 3.1, 3.3 | Concept/Question/Answer 模型、FSRS 间隔重复池、自适应状态机+mastery_state、StudyPlan planner、Kanban+dashboard、TerminalChallenge 模型、concept 关联 |
| 3.5 挑战目录与管理 | 3.1, 3.2, 3.4, 2.4 | challenge 数据模型+沙箱+bundle、多步+提示、Concept 关联筛选、dashboard 统一视图 |

---

## 技术选型决策（2026-06-23 yufeng 拍板）

1. **WebSocket 重连策略**：接受状态丢失。3.1 不引入 tmux 持久化，重连后新建 exec，容器内 shell 的 cwd/history/后台进程丢失（TTL 内复用同一容器）。先跑通闭环，后续迭代再评估 tmux wrapper。
2. **Docker SDK**：锁定 docker-py（Python 原生）。exec TTY stream 在 asyncio 下手动 pump stdin/stdout，PTY 处理虽比 subprocess CLI 复杂但类型友好、进程管理干净。
3. **镜像预构建**：只预构建 `quizcraft/sandbox:ubuntu`（部署时 docker-compose build）。alpine/centos 的 Dockerfile 留仓库内按需 `docker build`，不在部署时强制构建。3.5 多镜像支持保留，但默认仅 ubuntu。
4. **LLM verification 采集范围**（默认值）：命令历史 + check.sh 指定文件。opt-in per challenge，不做 rubric 细粒度评分。完整 rubric 评分后续迭代。
