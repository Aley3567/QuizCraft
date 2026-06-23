# 竞品研究: 文档出题工具

> Exa Agent Run 1 - high effort - 2026-06-23

## 市场分层

| 层级 | 代表产品 | 特点 |
|------|---------|------|
| 学生平台 | Quizlet, Knowt, Mindgrasp, Cramberry | 全流程学习，出题是功能之一 |
| 教师/评测 | QuestionWell, PrepAI, Questgen, Quillionz, QuizWhiz | 专注出题质量和 LMS 导出 |
| 轻量工具 | Smallpdf, SimpleQuizMaker, Quizzen, QuizMagic | "上传就出题"极简 |

## 关键商业产品

### Quizlet
- 格式: docx, pdf, pptx, Google Drive, 手写扫描
- 题型: MCQ + 写作题 + 闪卡
- AI: 未公开具体 LLM
- 痛点: 付费墙、手写识别差、生成内容过简、需手动修正

### Knowt
- 格式: PDF, PPT, Word, 视频, 音频, Google Drive
- 题型: 练习测试/闪卡
- 痛点: 广告多、扣费/取消问题、AI 不准确、精确匹配判分

### Revisely
- 格式: PDF, PPT, Word, 图片(含手写), 视频
- 题型: MCQ, 简答, 填空, 判断, AI 评分开放题
- 特色: 50+ 语言、AI 评分

### QuestionWell
- 格式: PDF, DOCX, PPTX, 图片, URL
- 题型: MCQ, 填空, 简答, 判断, 多选, 阅读理解, 词汇, 讨论题
- 特色: 教育标准对齐、Kahoot/Quizizz/Canvas 导出
- 痛点: 图片/表格解析差

### Questgen
- 格式: 文本, URL, PDF, Word, 图片, 音视频
- 题型: MCQ, 多选MCQ, 判断, 填空, FAQ, 简答, 高阶Q&A, 配对, Bloom分类
- 特色: 题型最全、导出格式最多 (QTI, Moodle XML, GIFT, AIKEN, CSV, JSON, PDF)

### QuizMagic
- 格式: PDF(含扫描), Word, PPT, Excel, 图片(含手写)
- 题型: MCQ, 判断, 填空, 简答, 论述
- 特色: **多模态 AI 直接读图表/手写，无需单独 OCR**；Bloom/SOLO 认知框架

## 开源项目

| 项目 | Stars | 技术栈 | 局限 |
|------|-------|--------|------|
| suncloudsmoon/quizzer | 16 | Python, OpenAI-compatible, SM-2 | CLI only, PDF only |
| ali-gur/mcq-generator | 3 | PyMuPDF/pdfplumber, GPT/Gemini/Claude | MCQ only |
| StephenGenusa/semantic-qa-gen | ? | Python, Tesseract OCR, OpenAI-compatible | 库而非成品 |
| AMontgomerie/question_generator | 299 | T5, BERT, spaCy | 已归档, 无文档上传 |
| kristiyanvachev/leaf-question-generation | 139 | T5 fine-tuned | 短文本, 无 PDF 支持 |

**结论**: 没有一个开源项目做到"多模态解析 + 多题型 + 闪卡 + FSRS + 终端闯关"。

## 用户普遍投诉 (跨产品)

1. 生成的题目太浅/太水/需要人工二次检查
2. 干扰项(错误选项)质量差，一看就是错的
3. 扫描 PDF、手写、公式、表格、图片解析经常出错
4. 不公开底层模型，隐私/准确性无法评估
5. 免费版限制多，核心 AI 功能在付费墙后面
6. 长文档处理是真正的差异化点——naive 全文 prompting 成本高且覆盖差
7. 数学/技术类/多语言/图片密集型内容仍是弱项
