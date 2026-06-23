/**
 * 答题状态纯函数：进度判定、计分、错题筛选、来源锚定展示。
 *
 * 刻意从 React 组件剥离为纯函数，便于 vitest 单测（UI 状态机仅做编排）。
 * 对齐 DESIGN_DECISIONS 4.3：错题反馈引用用户文档具体段落（页码 + 章节路径 + 原文片段）。
 */
import type { AnswerOut, QuestionOut, SourceSpan } from "./types";

/** answers 以 question_id 为键，便于乱序作答与重答（对齐后端幂等设计）。 */
export type AnswerMap = Record<number, AnswerOut>;

/** 是否所有题目都已作答。 */
export function isQuizComplete(answers: AnswerMap, questionIds: number[]): boolean {
  return questionIds.length > 0 && questionIds.every((id) => answers[id] != null);
}

/** 得分 = 正确数 / 总数；未答完或无题返回 null。 */
export function computeScore(answers: AnswerMap, questionIds: number[]): number | null {
  if (questionIds.length === 0) return null;
  if (!isQuizComplete(answers, questionIds)) return null;
  const correct = questionIds.filter((id) => answers[id]?.is_correct === true).length;
  return correct / questionIds.length;
}

/** 按题目顺序筛出答错的题（未作答不计入错题）。 */
export function wrongQuestions(
  questions: QuestionOut[],
  answers: AnswerMap,
): QuestionOut[] {
  return questions.filter((q) => answers[q.id]?.is_correct === false);
}

/** 把 source_span 渲染成「第X页（章节路径）」式可读引用；信息缺失回退「参考课件」。 */
export function formatSourceSpan(span: SourceSpan | null | undefined): string {
  if (!span) return "参考课件";
  const page = span.page != null ? `第${span.page}页` : null;
  const path = span.section_path ? `（${span.section_path}）` : null;
  const head = [page, path].filter(Boolean).join("");
  return head || "参考课件";
}

/** 取 source_span 原文片段，截断超长部分用于反馈展示（默认上限 120 字）。 */
export function sourceExcerpt(
  span: SourceSpan | null | undefined,
  max = 120,
): string {
  const text = span?.text?.trim();
  if (!text) return "";
  return text.length > max ? text.slice(0, max) + "…" : text;
}
