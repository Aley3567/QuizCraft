# QuizCraft Phase 4 垂直切片实施计划

> 基于 PRD_PHASE4.md + DESIGN_DECISIONS.md，按垂直切片思路拆解
> 2026-06-23 | 依赖 Phase 1 全部 5 个切片 + Phase 2 全部 5 个切片 + Phase 3 全部 5 个切片

---

## 切片划分思路

### 核心原则

1. **第一条切片是最小可用闭环**：选一个课程的闪卡集 → 生成合规 .apkg → Anki 导入验证 → FSRS 调度状态保留。这是 yufeng 最先想要的实用功能——把 QuizCraft 闪卡导到手机 AnkiDroid 上通勤复习。Anki 导出是纯逻辑、确定性测试 seam，不依赖多用户认证，可立即在 Phase 1-3 的单用户基础上跑通，立竿见影兑现"零供应商锁定"承诺。
2. **安全护栏第二条就立**：密码哈希（bcrypt，不可降级）、JWT 双 token + refresh rotation、数据隔离（user_id 全表过滤）、单用户→多用户迁移——全部在切片 4.2 立住，不延后不降级。Anki 导出放第一条是为了最快交付价值，认证紧跟第二条保证安全护栏在 Phase 4 早期就位，后续切片都建立在认证骨架之上。
3. **每条切片纵向贯穿**：从前端 UI 到后端 API 到数据库到外部格式（.apkg / ZIP / 反代）一条龙打通，不做"先做完所有认证端点再做 UI"或"先做完所有导出格式再做导入"的横向铺层。
4. **按价值递增**：Anki 导出闭环（4.1）-> 多用户认证骨架（4.2）-> 用户配置与管理（4.3）-> Anki 导入与替代格式（4.4）-> 数据可移植与 API 互通（4.5）-> 生产部署与运维监控（4.6）。先跑通最实用的导出，再立安全护栏，再补用户管理，再补导入方向和通用格式，再做全量可移植和 API 文档，最后收尾生产部署。
5. **Phase 4 多用户是数据层隔离，不改沙箱模型**：Phase 4 的多用户 = 每个用户看自己的数据（user_id 过滤），和 Phase 3 PRD 里 out-of-scope 的多用户沙箱 namespace 隔离是两回事。Phase 4 不改 Phase 3 的 Docker 沙箱隔离模型（unprivileged + no-new-privileges + --network none），沙箱仍是 Docker 默认隔离。明确这一点避免混淆——多用户共享一个 QuizCraft 实例时，终端挑战的沙箱容器不按用户 namespace 隔离，只靠 user_id 做数据层隔离。

### Phase 4 PRD 的 53 条 user stories 分布

| 切片 | 覆盖 stories | 说明 |
|------|-------------|------|
| 4.1 Anki 导出最小闭环 | 24, 25, 27, 28, 29 | 选 deck→生成 .apkg→FSRS→Anki 调度映射→Anki 导入验证，纯逻辑测试 seam |
| 4.2 多用户认证骨架 | 1, 2, 3, 9, 10, 11, 16, 17, 22, 23 | 注册/登录/JWT/refresh rotation/bcrypt/数据隔离/单用户迁移，安全护栏不可降级 |
| 4.3 用户配置与管理 | 4, 5, 7, 8, 12, 13, 14, 15, 18, 19, 20, 21 | 密码重置/注册模式/OAuth/profile/每用户 LLM+FSRS 配置/admin 用户管理与配额 |
| 4.4 Anki 导入与替代格式 | 26, 30, 31, 32, 33, 34, 35, 36 | .apkg 导入/SM-2→FSRS 转换/媒体提取/CSV/Markdown/PDF 学习指南 |
| 4.5 数据可移植与 API 互通 | 45, 46, 47, 48, 49, 50, 51, 52, 53 | 全量 ZIP 导出导入/OpenAPI/API 版本/Bearer token/统一错误格式 |
| 4.6 生产部署与运维监控 | 37, 38, 39, 40, 41, 42, 43, 44 | 生产 Docker Compose/HTTPS/环境变量/备份恢复/升级迁移/health/资源监控 |

---

## 切片 4.1：Anki 导出最小闭环

**目标**：yufeng 选一个课程的闪卡集，点击导出，系统生成合规 .apkg 文件，下载后在 Anki 桌面/手机导入，闪卡带 FSRS 调度状态继续复习。这是 Phase 4 最先让 yufeng 用上的实用功能，也是确定性测试 seam——纯逻辑，无 LLM、无认证依赖。

**用户价值**：做完这个切片后，yufeng 在 QuizCraft 里积累的闪卡不再锁在本系统里——导出 .apkg 到手机 AnkiDroid，通勤时刷卡片，FSRS 调度进度不丢。这是"零供应商锁定"承诺的第一次兑现，也是 QuizCraft 接入 Anki 生态（全球最大闪卡用户群）的入口。

**预估天数**：10 天

### 任务清单

**Anki .apkg 格式研究 + 写入器（3 天）**
- .apkg = ZIP(collection.anki21 + media JSON)，collection.anki21 是 SQLite 数据库
- SQLite schema 研究：col（collection config）, notes, cards, decks, deck_config, notetypes, review_logs 表结构
- `AnkiExporter` 服务层：输入 = flashcards 列表 + FSRS 状态，输出 = .apkg 字节流
- 用 genanki 库生成 .apkg（yufeng 拍板：推翻 PRD 手写决策，规避手写 Anki SQLite schema 风险，genanki 成熟 BSD 库）
- 创建自定义 note type "QuizCraft"：fields = [Front, Back, Source, Tags]，templates = [Forward (Front→Back)]
- deck 创建：每个导出的课程对应一个 Anki deck
- note/card 关系：一个 note 生成一张 card（Forward template）

**FSRS → Anki 调度字段映射（2 天）**
- 调度字段映射（PRD 表）：
  - `state` (new/learning/review/relearning) → `type` (0=new, 1=learning, 2=review, 3=relearning) 直接枚举映射
  - `due_date` → `due`（review 卡用 epoch-days，learning 卡用 epoch-ms）
  - `stability` → Anki `data` JSON 字段 `{"s": value}`（Anki 23.10+ FSRS 识别）
  - `difficulty` → Anki `data` JSON 字段 `{"d": value}`
  - `reps` / `lapses` → 直接复制
  - `last_review` → `odue` 或计算推导
- 导出时 Anki deck config 设为 FSRS 模式，确保 Anki 读取 data 字段
- 验证 Anki 23.10+ 识别 FSRS 参数（实际导入测试）

**导出 API + 前端（2 天）**
- POST /api/flashcards/export-apkg：参数 = course_id 或 document_id（选哪些 deck 导出，不强制全导）
- 响应 = .apkg 文件下载（FastAPI StreamingResponse）
- 前端导出入口：课程详情页 / 闪卡列表页新增"导出到 Anki"按钮
- 导出选择 UI：勾选要导出的课程/文档
- 导出进度提示（大 deck 耗时，异步生成 + 下载链接）

**Anki 导入验证 + 测试（3 天）**
- 实际用 Anki 桌面客户端导入导出的 .apkg，验证：
  - 卡片数量正确
  - Front/Back/Source/Tags 字段填充正确
  - FSRS 调度状态保留（已掌握卡不重置为新卡）
  - CJK 字符编码正确
- 单元测试覆盖 PRD Seam 2（Anki 导出端用例）：
  - 10 张卡导出 → ZIP 含合法 SQLite 数据库
  - note count + 字段填充 + notetype "QuizCraft" 存在
  - FSRS→Anki 字段映射（stability=30.0, difficulty=5.5, state=review → Anki card 正确 type/ivl/data）
  - CJK 字符编码正确
- round-trip 测试在切片 4.4 完整实现（导出→导入回来），4.1 先验证导出端

### 验收标准

- [ ] 选一个课程的闪卡集，点击"导出到 Anki"，下载 .apkg 文件
- [ ] Anki 桌面客户端导入 .apkg 成功，无报错
- [ ] 导入后卡片显示 Front/Back/Source/Tags 四个字段
- [ ] 已掌握的闪卡在 Anki 中仍为 review 状态（不重置为新卡）
- [ ] 可选择导出部分课程/文档（不强制全导）
- [ ] 卡片带 tags（课程名、文档来源、概念名）
- [ ] CJK 字符在 Anki 中显示正确
- [ ] 导出器通过单元测试（PRD Seam 2 导出端用例）

### 依赖

- Phase 1 切片 1.3（Flashcard 数据模型 + FSRS 调度字段——导出的数据源）
- Phase 1 切片 1.5（Docker Compose 部署——导出功能在已有部署上运行）
- Phase 2 切片 2.5（Course 模型——课程级闪卡集导出）

---

## 切片 4.2：多用户认证骨架（安全护栏）

**目标**：从 Phase 1 单密码认证升级到完整多用户系统——注册/登录/JWT 双 token + refresh rotation/bcrypt 密码哈希/全表 user_id 数据隔离/单用户→多用户迁移命令。安全护栏在第二条切片就立住，不延后不降级。这是 Phase 4 风险最高的切片（数据迁移 + 安全敏感）。

**用户价值**：做完这个切片后，yufeng 可以把 QuizCraft 部署到实验室服务器或学习小组共享——每个人注册自己的账号，只看到自己的课程和闪卡，互不干扰。现有 Phase 1-3 的数据通过迁移命令无损升级，第一个注册用户自动成为 admin。

**预估天数**：14 天

### 任务清单

**用户数据模型 + 密码哈希（2 天）**
- `users` 表建表：id, email (unique), password_hash, display_name, role (user/admin), is_active, created_at, last_active_at
- `refresh_tokens` 表：id, user_id, token_hash, expires_at, revoked_at, replaced_by (token rotation 链), created_at
- bcrypt 集成（cost factor 12，不可降级——PRD 明确 bcrypt only，无 SHA-256/MD5/homebrew）
- 密码校验：最小 8 字符，无最大长度（bcrypt 72 字节截断在 UI 文档说明）
- `User` SQLAlchemy 模型 + repository 层

**JWT 签发 + refresh rotation（2 天）**
- JWT 库：PyJWT（HS256 签发 + 验证）
- access token：HS256，15 分钟有效，payload = {user_id, role, exp}，前端存内存（非 localStorage，防 XSS 窃取）
- refresh token：opaque 随机串，存 DB refresh_tokens 表，7 天有效，httpOnly secure cookie
- refresh rotation：每次用 refresh 换新 access 时，旧 refresh 失效 + 签发新 refresh
- token family 失效检测：被替换的 refresh 再次被用时，整个 token family 失效（检测 token 盗用）
- `QUIZCRAFT_JWT_SECRET` 环境变量必须配置，未配置拒绝启动（不 fallback 默认 key——PRD 安全要求）

**注册/登录/登出 API + rate limit（2 天）**
- POST /api/auth/register：email + password，返回 user info（不含 password_hash）
- POST /api/auth/login：email + password，constant-time 比较（防时序侧信道），返回 access token + set refresh cookie
- POST /api/auth/refresh：用 refresh cookie 换新 access + rotation
- POST /api/auth/logout：撤销当前 refresh token
- rate limit：登录 5 次/分钟/IP，注册 3 次/小时/IP
- 重复 email 注册 → 409 Conflict
- 错误密码 → 401，constant-time 比较

**全表 user_id + 数据隔离（3 天）**
- 所有业务表加 `user_id` FK（PRD 列出的全部表）：documents, sections, concepts, questions, quiz_sessions, answers, flashcards, review_logs, courses, course_documents, course_concepts, study_plans, daily_plans, plan_tasks, terminal_challenges
- `UserScopedQuery` mixin / repository base class：自动在所有查询加 `WHERE user_id = current_user.id`，强制在 ORM 层而非每个端点 ad-hoc
- admin 端点可 bypass（仅聚合查询，不读个别用户数据除非显式）
- 所有现有 API 端点接入 user_id 过滤
- 数据隔离测试：User A 的数据 User B 查不到；User B 按 ID 直接访问 User A 的文档 → 404（非 403，防 ID 枚举）

**单用户→多用户迁移命令（2 天）**
- CLI 命令 `quizcraft migrate`（离线迁移，非启动时自动——PRD 要求操作者控制时机）
- 迁移步骤（PRD）：
  1. 创建 users + refresh_tokens 表
  2. 提示创建 admin 账号（email + password，或 env var QUIZCRAFT_ADMIN_EMAIL/PASSWORD）
  3. 全表加 user_id 列，默认 admin user id
  4. 加 NOT NULL + FK 约束
  5. user_id 加入复合索引（查询性能）
- 幂等设计：失败可重跑完成；pre-migration 强制提示备份
- fresh instance 第一个注册用户自动 admin

**前端登录/注册页 + token 管理（2 天）**
- /login 页：email + password 登录
- /register 页：email + password 注册（注册模式由后端控制，切片 4.3 完善）
- access token 存内存（React context/state），刷新时用 httpOnly refresh cookie
- 401 拦截：access 过期自动 refresh，refresh 失效跳转登录
- 顶部用户菜单：显示 email、登出按钮
- 未登录访问任何页面跳转登录（保留 Phase 1 的认证中间件升级）

**测试（1 天）**
- 集成测试覆盖 PRD Seam 1 全部 15 条用例（FastAPI test client，完整请求-响应周期）

### 验收标准

- [ ] 注册新账号（email + password），密码以 bcrypt 哈希存储（不可逆）
- [ ] 登录返回 access token + refresh cookie
- [ ] access token 15 分钟过期，过期后自动 refresh
- [ ] refresh token rotation：每次刷新旧 token 失效
- [ ] 被盗 refresh token 重放 → 整个 token family 失效
- [ ] 改密码后所有 session 失效
- [ ] User A 的课程/文档/闪卡 User B 看不到
- [ ] User B 按 ID 直接访问 User A 的文档 → 404（非 403）
- [ ] 非管理员访问 admin 端点 → 403
- [ ] 单用户数据迁移：现有 Phase 1-3 数据全部归属 admin，无损
- [ ] QUIZCRAFT_JWT_SECRET 未配置时拒绝启动
- [ ] 登录 rate limit 生效（5 次/分钟/IP）
- [ ] 认证系统通过集成测试（PRD Seam 1，15 条用例）

### 依赖

- Phase 1 切片 1.1（数据模型分层——全表加 user_id FK）
- Phase 1 切片 1.5（密码认证基础——升级替换，不破坏现有 session 体验）
- Phase 2 切片 2.5（Course 模型——user_id 加到 course 相关表）
- Phase 3 切片 3.1（TerminalChallenge 模型——user_id 加到 terminal_challenges 表）

---

## 切片 4.3：用户配置与管理

**目标**：完善多用户系统——密码重置、注册模式控制（open/invite/disabled）、用户个人资料、每用户 LLM 配置与 FSRS 参数、admin 用户管理面板（列表/禁用/删除/统计/配额）。OAuth 基础框架落地（GitHub 单 provider，Google 延后）。

**用户价值**：做完这个切片后，yufeng 可以控制谁注册（开放/邀请码/关闭）、每人用自己的 LLM key 和 FSRS 偏好、admin 能管理用户和监控资源占用。OAuth 让 GitHub 登录免去记密码的麻烦。

**预估天数**：12 天

### 任务清单

**密码重置（2 天）**
- POST /api/auth/forgot-password：email → 生成重置 token（短期 30 分钟）→ 发邮件
- POST /api/auth/reset-password：token + 新密码 → 验证 → 更新 bcrypt hash → 失效所有 session
- 邮件发送：SMTP 配置（环境变量），简化模板
- 未配置 SMTP 时降级：重置 token 显示在 CLI/日志（开发模式，保证功能可用）

**注册模式控制（1 天）**
- `QUIZCRAFT_REGISTRATION` 环境变量：open（默认）/invite/disabled
- invite 模式：admin 生成邀请码，注册需有效码，注册后码消耗
- disabled 模式：注册端点返回 403，admin 手动创建账号
- 前端注册页根据模式隐藏/显示邀请码字段

**OAuth 基础框架（2 天）**（降级处理：GitHub only，Google 延后）
- authlib 集成，OAuth2 Authorization Code Grant
- GitHub provider 实现（可独立开关 via OAUTH_GITHUB_CLIENT_ID/SECRET）
- 账号合并：email 匹配——已注册 email + OAuth 同 email → 自动关联
- 未配置 OAuth 时登录页隐藏 OAuth 按钮
- Google provider 延后（见延后表）

**用户资料与偏好（3 天）**
- GET/PUT /api/users/me：display_name, email（改 email 触发验证）
- 每用户 LLM 配置：provider, api_key, model, base_url
  - API key AES-256 加密存储（key 从 QUIZCRAFT_JWT_SECRET 派生）
  - API key 永不在 API 响应中返回
- 每用户 FSRS 参数：desired_retention, daily_new_limit, daily_review_limit
- Phase 1 切片 1.2 的 LLM 配置从全局改为 per-user（保留全局默认作 fallback）
- Phase 1 切片 1.3 的 FSRS 参数从全局改为 per-user（保留全局默认作 fallback）

**session 管理（1 天）**
- GET /api/users/me/sessions：活跃 session 列表（device, last_active, ip）
- DELETE /api/users/me/sessions/{id}：撤销指定 session
- 改密码 / 改 email 触发全 session 失效

**admin 用户管理（3 天）**
- GET /api/admin/users：用户列表（email, display_name, role, 注册日期, last_active, storage_used）
- POST /api/admin/users/{id}/disable：禁用账号（is_active=false，数据保留）
- DELETE /api/admin/users/{id}：删除账号（级联删除数据，需二次确认）
- POST /api/admin/users/{id}/promote：提升为 admin
- POST /api/admin/users/{id}/quota：设置存储配额
- 前端 admin 面板：用户表格 + 操作按钮

### 验收标准

- [ ] 忘记密码 → 收到重置邮件 → 重置成功 → 所有旧 session 失效
- [ ] 注册模式 = invite 时，无邀请码注册返回 403
- [ ] 注册模式 = disabled 时，注册端点返回 403
- [ ] GitHub OAuth 登录成功（未配置时按钮隐藏）
- [ ] OAuth 账号与同 email 已注册账号自动合并
- [ ] 用户可在 profile 设置 display_name、email、LLM 配置、FSRS 参数
- [ ] LLM API key 加密存储，响应中不返回
- [ ] 每用户的 LLM 配置独立（A 的 key 不影响 B）
- [ ] 可查看活跃 session 列表并撤销
- [ ] admin 可列出所有用户、禁用、删除、提升、设配额
- [ ] 非管理员访问 admin 端点 → 403

### 依赖

- 切片 4.2（users 表、JWT、数据隔离、UserScopedQuery）
- Phase 1 切片 1.2（LLM 配置——从全局改为 per-user）
- Phase 1 切片 1.3（FSRS 参数——从全局改为 per-user）

---

## 切片 4.4：Anki 导入与替代导出格式

**目标**：Anki .apkg 导入方向（.apkg → QuizCraft 闪卡，含 SM-2→FSRS 转换和媒体提取）+ CSV/Markdown/PDF 导出 + 补回切片 4.1 延后的图片媒体导出。让 yufeng 既能把现有 Anki 卡片库搬进 QuizCraft 用自适应引擎，也能用通用格式备份分享。

**用户价值**：做完这个切片后，yufeng 手里 2000 张 Anki 卡片可以直接导入 QuizCraft 享受自适应学习，不用手动重建。还能导出 CSV/Markdown 给其他工具或打印复习表。Anki 双向互通闭环完成。

**预估天数**：9 天

### 任务清单

**Anki .apkg 导入器（3 天）**
- `AnkiImporter` 服务：解压 .apkg → 读 collection.anki21 SQLite → 解析 notes/cards/notetypes
- note type 识别：QuizCraft note type 直接映射 Front/Back/Source/Tags；其他 note type best-effort 映射（第 1 字段→Front，第 2 字段→Back）
- 导入为新课程或加入现有课程（用户选择）
- 导入的卡片创建为 Flashcard 记录，关联新 Course

**SM-2 → FSRS 调度转换（1 天）**
- Anki legacy SM-2 卡片转换：stability ≈ ivl * 0.9，difficulty ≈ 11 - factor/100（PRD 公式）
- 导入卡进入 FSRS review 状态（近似参数）
- FSRS 感知的 Anki 卡（有 data 字段）→ 直接读取 stability/difficulty

**媒体处理（1 天）**
- .apkg media 文件提取到 QuizCraft 文档存储
- HTML `<img src="...">` 引用重写为 QuizCraft media endpoint
- 补回切片 4.1 延后的 Story 26：导出时闪卡 HTML 中的图片打包进 .apkg media store

**CSV 导出（1 天）**
- GET /api/flashcards/export-csv：front, back, tags, source 列
- 前端导出按钮（与 Anki 导出并列）

**Markdown 导出（1 天）**
- GET /api/flashcards/export-markdown：一卡一节，## Front / 内容 / ## Back / 内容
- 可读性优先，便于打印/搜索

**PDF 学习指南导出（1 天）**（降级处理：基础版，不排版美化）
- GET /api/questions/export-study-guide：题目 + 正确答案，Markdown → PDF（weasyprint 或 md-to-pdf）
- 按课程/文档组织，含目录

**测试（1 天）**
- 单元测试覆盖 PRD Seam 2 导入端用例 + round-trip
- round-trip：QuizCraft 导出（切片 4.1）→ 导入回来 → 卡数 + 文本 + FSRS 状态匹配（浮点容差）

### 验收标准

- [ ] 导入一个 Anki .apkg 文件，闪卡出现在 QuizCraft（为新课程或加入现有课程）
- [ ] Anki FSRS 卡片的 stability/difficulty 保留
- [ ] Anki SM-2 卡片近似转换为 FSRS 参数
- [ ] .apkg 中的图片提取并显示在卡片上
- [ ] 导出 CSV 可在 Excel/Google Sheets 打开
- [ ] 导出 Markdown 可读，一卡一节
- [ ] 导出 PDF 学习指南含题目 + 答案
- [ ] round-trip：导出→导入→卡数+文本+FSRS 状态匹配
- [ ] 导入器通过单元测试（PRD Seam 2 导入端 + round-trip）

### 依赖

- 切片 4.1（.apkg 格式研究 + AnkiExporter——导入复用格式知识）
- Phase 1 切片 1.3（Flashcard 模型 + FSRS 调度）
- Phase 2 切片 2.5（Course 模型——导入为新课程）

---

## 切片 4.5：数据可移植与 API 互通

**目标**：全量用户数据导出/导入 ZIP（含文档原文件）+ OpenAPI/Swagger 文档 + API 版本前缀 + Bearer token 程序化访问 + 统一错误格式。让用户数据完全可移植、API 对第三方集成友好。

**用户价值**：做完这个切片后，yufeng 可以一键导出全部数据（课程/文档/题目/闪卡/复习记录）到 ZIP，迁移到新服务器零丢失。第三方开发者可以照着 OpenAPI 文档写 Obsidian 插件、CLI 工具对接 QuizCraft。这是 QuizCraft 从个人工具变成正经开源项目的关键。

**预估天数**：9 天

### 任务清单

**全量数据导出（2 天）**
- POST /api/data/export：生成 ZIP（PRD 结构）
  - manifest.json（schema_version, 导出日期, user info, 内容摘要）
  - courses/, documents/, questions/, flashcards/, review-history/, quiz-sessions/, settings.json
  - 文档原文件（PDF/DOCX）打包进 documents/
- 异步生成（大数据库耗时）+ 下载链接
- LLM API key 不导出（安全——PRD 明确）

**全量数据导入（2 天）**
- POST /api/data/import：上传 ZIP → 解析 manifest → 预览（数量摘要）
- 确认后导入：所有记录重新生成 UUID（不 merge，不冲突——PRD 决策）
- 导入到新课程（如已有数据不破坏）
- schema_version 校验：未来版本拒绝并报错
- 损坏 ZIP 优雅报错（无半成品状态）

**导入预览（1 天）**
- 导入前显示：课程数、文档数、闪卡数、复习记录数
- 用户确认后执行导入

**OpenAPI 文档（1 天）**
- FastAPI 自动生成 OpenAPI spec（整理 + 暴露 /docs 和 /redoc）
- 确保所有端点有 docstring + response model
- 文档对外可访问，无需认证

**API 版本前缀（1 天）**
- 所有端点移到 /api/v1/ 前缀（APIRouter prefix 实现）
- 无版本路径 /api/... 重定向到 /api/v1/（过渡期）
- OpenAPI docs 按版本生成

**Bearer token + 统一错误格式（2 天）**
- Bearer token 支持：除 session cookie 外，支持 Authorization: Bearer <access_token> 用于程序化访问
- 统一错误响应：{status_code, error_code, message}
- 全端点错误格式统一（现有端点的错误响应改造）

### 验收标准

- [ ] 导出 ZIP 结构符合 PRD 规范（manifest.json + 各子目录）
- [ ] manifest.json 含 schema_version 和内容计数
- [ ] 导出 ZIP 含文档原文件（PDF/DOCX）
- [ ] LLM API key 不在导出中
- [ ] 导入 ZIP 到新实例，所有记录恢复（课程→文档→概念→题目→闪卡关系完整）
- [ ] 导入的 FSRS 状态匹配原数据
- [ ] 导入到已有数据的实例，不冲突（新 UUID）
- [ ] 导入前显示预览（数量摘要）
- [ ] 损坏 ZIP 优雅报错，无半成品状态
- [ ] 未来 schema_version 拒绝导入
- [ ] /docs 可访问 OpenAPI 文档
- [ ] 所有端点在 /api/v1/ 下
- [ ] Bearer token 可用于程序化访问
- [ ] 错误响应格式统一
- [ ] 数据导出导入通过集成测试（PRD Seam 3，7 条用例）

### 依赖

- 切片 4.2（user_id 隔离——导出当前用户数据）
- Phase 1 全部 5 个切片（所有业务数据模型——导出全量数据）
- Phase 2 全部 5 个切片（Course/StudyPlan/PlanTask/Kanban 数据）
- Phase 3 切片 3.1（TerminalChallenge 数据——含在导出中）

---

## 切片 4.6：生产部署与运维监控

**目标**：生产级 Docker Compose + HTTPS 反代指导 + 环境变量参考 + 备份恢复流程 + 版本升级迁移文档 + /health 端点 + 资源监控面板。让 QuizCraft 能被其他人可靠地生产部署，从"我的机器上能跑"到"别人也能可靠跑"。

**用户价值**：做完这个切片后，yufeng 或任何社区用户可以照着文档把 QuizCraft 部署到 VPS，配好 HTTPS 和备份流程，/health 接入 uptime 监控，admin 面板看资源占用。这是 Phase 4 收尾，也是 QuizCraft 成为正经开源项目的最后一块。

**预估天数**：9 天

### 任务清单

**生产 Docker Compose + HTTPS（2 天）**
- 生产 docker-compose.prod.yml：frontend + backend + Caddy 反代（主推，自动 HTTPS）
- HTTPS 终止：Caddy 自动 ACME 证书
- 生产环境变量：QUIZCRAFT_JWT_SECRET, DB_PATH, LLM 默认配置, CORS origins
- 不含开发用的 debug 配置

**环境变量参考文档（1 天）**
- 完整环境变量清单：数据库路径、LLM 默认、认证密钥、CORS、rate limit、OAuth、注册模式、SMTP
- .env.example 文件 + README 文档（不读源码即可配置）

**备份恢复指南（1 天）**
- 备份：SQLite 文件 + 上传文档目录的 cron 备份脚本
- 恢复：还原 SQLite + 文档目录的步骤
- 文档化的备份/恢复流程（Phase 4 不做自动备份守护进程，PRD out of scope——操作者用 cron + 文档）

**版本升级迁移文档（1 天）**
- 升级步骤：备份数据库 → 拉新镜像 → 运行 alembic migrate / quizcraft migrate → 验证
- 破坏性变更文档
- 回滚步骤：恢复备份（Phase 4 不支持 schema 自动回滚——PRD 要求回滚靠恢复备份）

**/health 端点（1 天）**
- GET /health（无需认证，可接入 uptime 监控）
- 返回 JSON（PRD 格式）：status (healthy/degraded/unhealthy), version, checks{database, disk, llm}, timestamp
- database: 连通性 + 延迟
- disk: 剩余空间
- llm: 可选（实例级 LLM 配置连通性，非用户级）

**资源监控面板（2 天）**
- admin 面板：存储用量（文档总大小、数据库大小）
- LLM API 调用计数 + 估算成本（per user 聚合）
- 复用 Phase 1 切片 1.5 的成本估算基础，扩展为 per-user
- 前端 admin dashboard 页面（与切片 4.3 的 admin 用户管理合并为统一 admin 面板）

**测试与文档收尾（1 天）**
- 生产部署端到端验证（VPS 或本地模拟）
- 文档完整性检查

### 验收标准

- [ ] docker-compose.prod.yml 一键启动生产部署
- [ ] HTTPS 反代配置有效（自动证书）
- [ ] 环境变量文档完整，无阅读源码即可配置
- [ ] 备份脚本可执行，恢复流程文档化
- [ ] 升级迁移文档清晰（备份→迁移→验证→回滚）
- [ ] /health 返回结构化 JSON，含各组件状态
- [ ] /health 接入 uptime 监控可用（无需认证）
- [ ] admin 面板显示存储用量和 LLM 成本
- [ ] 生产部署端到端验证通过

### 依赖

- Phase 1 切片 1.5（Docker Compose 开发部署——升级到生产）
- 切片 4.2（认证配置——生产 JWT secret）
- 切片 4.3（admin 面板——监控面板复用 admin 基础）
- Phase 3 切片 3.1（docker.sock 配置——生产部署需兼容沙箱）

---

## 延后/砍掉的 User Stories

### 延后到 Phase 4+ 的 Stories

| Story | 内容 | 延后理由 |
|-------|------|---------|
| 6 | Google OAuth 登录 | 切片 4.3 实现 GitHub OAuth 验证流程跑通；Google provider 配置逻辑相同，验证完 GitHub 后可快速复制。yufeng 个人自部署优先 GitHub 足够，Google OAuth（大学 Google 账号场景）延后到后续迭代。 |
| 自动备份 | PRD 已明确 out of scope | Phase 4 文档化备份流程 + 提供 cron 脚本，不做定时自动备份守护进程。操作者用 cron + 文档。 |

### 切片内降级处理的 Stories

| Story | PRD 原文 | 切片内处理方式 | 理由 |
|-------|---------|--------------|------|
| 5 | GitHub OAuth 登录 | 切片 4.3 实现 GitHub OAuth 完整流程；Google（Story 6）延后。先单 provider 验证 OAuth 框架。 | 两 provider 逻辑相同，先跑通一个再复制另一个，避免并行调试两个 OAuth App 配置。 |
| 26 | 导出 .apkg 含图片 | 切片 4.1 仅导出文本闪卡（无图片）；切片 4.4 补媒体提取 + 打包。 | 文本闪卡导出覆盖 90% 场景，媒体处理涉及 HTML 解析 + 文件打包，复杂度高，先跑通核心导出闭环。 |
| 4 | 密码重置邮件 | 切片 4.3 实现邮件重置；未配置 SMTP 时降级为 CLI/日志输出 token（开发模式）。 | 自部署可能无 SMTP，开发模式降级保证功能可用，生产配 SMTP 后自动切换。 |
| 33 | Anki 导入媒体提取 | 切片 4.4 实现基础媒体提取（图片 + 音频）；不做视频等罕见媒体类型。 | 图片音频覆盖常见场景，罕见媒体类型延后。 |
| 36 | PDF 学习指南导出 | 切片 4.4 实现基础版：题目 + 答案 Markdown → PDF（weasyprint）；不做排版美化、不分难度筛选。 | 先保证可打印可读，排版美化后续迭代。 |

### 明确不做的（Phase 4 范围内但技术上简化）

- **多用户沙箱 namespace 隔离**：Phase 4 的多用户是数据层隔离（user_id 过滤），不改 Phase 3 的 Docker 沙箱隔离模型。沙箱仍是 Docker 默认隔离（unprivileged + no-new-privileges + --network none），不为多用户引入 namespace 配额。与 Phase 3 PRD out-of-scope 的多用户沙箱隔离是两回事，明确区分避免混淆。
- **AnkiWeb sync 协议**：只做 .apkg 文件导入导出，不实现 AnkiWeb 双向实时同步。PRD out of scope。
- **用户间数据共享**：不做"分享课程给好友"功能。数据完全隔离，分享靠导出文件。PRD out of scope。
- **自动定时备份**：文档化备份流程，不做定时备份守护进程。PRD out of scope。
- **SSO/SAML/LDAP**：只做 OAuth（GitHub），企业 IdP out of scope。PRD out of scope。
- **细粒度 RBAC**：只有 user/admin 两角色，不做 per-course 权限、viewer/editor 角色。PRD out of scope。
- **移动 app**：QuizCraft 保持桌面优先 web 应用，Anki 导出覆盖移动闪卡复习场景。PRD out of scope。

---

## 总工期与节奏

| 切片 | 预估天数 | 累计 |
|------|---------|------|
| 4.1 Anki 导出最小闭环 | 10 | 10 |
| 4.2 多用户认证骨架 | 14 | 24 |
| 4.3 用户配置与管理 | 12 | 36 |
| 4.4 Anki 导入与替代格式 | 9 | 45 |
| 4.5 数据可移植与 API 互通 | 9 | 54 |
| 4.6 生产部署与运维监控 | 9 | 63 |

yufeng 业余时间开发，按每周 10-15 小时折算约 8-9 周可完成全部 6 个切片。切片 4.1 完成后即可把闪卡导到手机 Anki 复习（最实用价值先交付），切片 4.2 立安全护栏（Phase 4 内早立），切片 4.3 补用户管理，切片 4.4 完成 Anki 双向互通闭环，切片 4.5 兑现数据可移植承诺，切片 4.6 收尾生产部署。切片 4.2 是最重也最关键的切片（数据迁移 + 安全敏感 + 全表改 schema），完成后即可多人共享部署。

---

## 跨 Phase 依赖说明

| Phase 4 切片 | 依赖的 Phase 1/2/3 切片 | 依赖内容 |
|-------------|------------------------|---------|
| 4.1 Anki 导出 | 1.3, 1.5, 2.5 | Flashcard 模型 + FSRS 调度字段（导出数据源）、Docker 部署基础、Course 模型（课程级导出） |
| 4.2 多用户认证 | 1.1, 1.5, 2.5, 3.1 | 数据模型分层（全表加 user_id FK）、密码认证基础（升级替换）、Course 模型（user_id 加 course 表）、TerminalChallenge 模型（user_id 加 terminal_challenges 表） |
| 4.3 用户配置与管理 | 4.2, 1.2, 1.3 | users 表 + JWT + 数据隔离、LLM 配置（改 per-user）、FSRS 参数（改 per-user） |
| 4.4 Anki 导入与替代格式 | 4.1, 1.3, 2.5 | .apkg 格式研究 + AnkiExporter（复用格式知识）、Flashcard 模型 + FSRS、Course 模型（导入为新课程） |
| 4.5 数据可移植与 API 互通 | 4.2, 1.1-1.5, 2.1-2.5, 3.1 | user_id 隔离（导出当前用户数据）、全部业务数据模型（导出全量数据：Document/Section/Concept/Question/Flashcard/Course/StudyPlan/TerminalChallenge） |
| 4.6 生产部署与运维监控 | 1.5, 4.2, 4.3, 3.1 | Docker Compose 开发部署（升级生产）、认证配置（生产 JWT secret）、admin 面板（监控面板复用）、docker.sock 配置（生产兼容沙箱） |

---

## 技术选型决策（2026-06-23 yufeng 拍板）

1. **JWT 库**：PyJWT（轻量，只需 HS256 签发 + 验证，社区活跃）。python-jose 的 JWS/JWE/JWK 全套能力用不上。
2. **密码哈希**：bcrypt（cost factor 12，不可降级）。尊重 PRD 决策，72 字节截断在 UI 文档说明。argon2id 更现代但 bcrypt 久经考验，个人项目足够。
3. **Anki .apkg 生成**：改用 genanki 库（**推翻 PRD 手写决策**）。genanki 成熟开源（BSD 许可、活跃维护），规避手写 Anki SQLite schema（col/notes/cards/decks/notetypes 表结构 + 内部 ID 约定）的高风险，4.1 能稳稳跑通。引入一个依赖换取可靠性。
4. **OAuth provider**：GitHub only（Google 延后到后续迭代，验证完 GitHub 流程后可快速复制）。
5. **生产反向代理**：Caddy（主推，配置最简 + 自动 HTTPS ACME，适合个人部署）。文档另附 Nginx + certbot、Traefik 示例配置。
6. **备份策略**：纯文档 + cron 示例脚本（不做自动备份守护进程，PRD out-of-scope）。
7. **refresh token 存储**：SQLite 表（不引入 Redis，个人自部署足够）。
8. **JWT vs server-side session**：JWT + refresh rotation + token family 失效检测（PRD 方案，已覆盖主动撤销需求）。
