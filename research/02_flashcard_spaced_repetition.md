# 竞品研究: 闪卡与间隔重复

> Exa Agent Run 2 - high effort - 2026-06-23

## 核心趋势

1. **FSRS 正在替代 SM-2**: Anki 23.10+, AnkiDroid, RemNote, Mochi, Obsidian 插件都在迁移
2. **AI 转移了瓶颈**: 从"调度算法"转向"内容自动生成"——RemNote/Brainscape 已支持从文档生成卡片
3. **笔记+卡片融合**: RemNote, Mochi, Obsidian 把卡片嵌入笔记上下文，减少手动创建摩擦
4. **本地优先/隐私**: Obsidian 插件, Mochi, Recall, Pupil 等面向不想云锁定的用户
5. **算法 UX 从"调参数"变成"管记忆率/工作量"**: FSRS 的目标记忆率、负载均衡、休假恢复等

## 间隔重复算法对比

| 算法 | 优点 | 缺点 | 使用者 | 开源实现 |
|------|------|------|--------|---------|
| SM-2 | 简单透明，几十年验证 | 参数固定，无记忆率目标，逾期处理差 | Anki 旧模式, 老闪卡应用 | anki-sm-2 (Python) |
| **FSRS** | **ML 自适应，目标记忆率，逾期平滑** | 需要历史数据才最优 | **Anki 23.10+, RemNote, Mochi** | **ts-fsrs / py-fsrs / fsrs-rs** |
| SM-18 | 深度记忆建模 | 专有，仅 SuperMemo | SuperMemo 18 | 无 |
| Brainscape CBR | 简单用户友好 | 专有不透明 | Brainscape | 无 |
| Leitner | 极简可实现 | 粗糙无个性化 | 纸质闪卡 | spacedreppy |

## 关键开源库

| 库 | 语言 | 算法 | 用途 |
|----|------|------|------|
| **ts-fsrs** | TypeScript | FSRS v6 | 前端调度 |
| **py-fsrs** | Python | FSRS | 后端调度+优化器 |
| fsrs-rs | Rust | FSRS | 高性能/WASM |
| free-spaced-repetition-scheduler | 多语言 Hub | FSRS | 各语言入口 |
| anki-sm-2 | Python | SM-2 | 兼容/迁移 |
| spacedreppy | Python | SM-2/Leitner/FSRS-6 | 多算法比较 |

## 设计建议 (来自研究)

1. 默认 FSRS，保留 SM-2 导入/导出兼容
2. 存储 review logs + stability/difficulty/desired_retention + 算法版本，支持迁移
3. 工作量控制：每日新卡上限、复习量预测、休假恢复、leech 检测、归档
4. AI 生成的卡片必须可预览/编辑/溯源/去重
5. 数据可移植：支持 Anki .apkg/CSV/Markdown 导出
