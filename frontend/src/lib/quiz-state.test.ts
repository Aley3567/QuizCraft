import { describe, expect, it } from "vitest";

import type { AnswerOut, QuestionOut, SourceSpan } from "../lib/types";
import {
  computeScore,
  formatSourceSpan,
  isQuizComplete,
  sourceExcerpt,
  wrongQuestions,
} from "../lib/quiz-state";

function ans(isCorrect: boolean): AnswerOut {
  return {
    id: 1,
    quiz_session_id: 1,
    question_id: 1,
    selected_option_index: 0,
    is_correct: isCorrect,
    feedback: "x",
  };
}

function mkQ(id: number, span?: Partial<SourceSpan>): QuestionOut {
  return {
    id,
    concept_id: null,
    section_id: null,
    question_type: "multiple_choice",
    stem: `Q${id}`,
    options: ["a", "b"],
    correct_option_index: 0,
    explanation: null,
    source_span: {
      page: span?.page ?? 12,
      section_path: span?.section_path ?? "第一章",
      text: span?.text ?? "原文片段",
    },
    bloom_level: null,
    difficulty: null,
    self_eval_score: null,
  };
}

describe("isQuizComplete", () => {
  it("全部题目作答才算完成", () => {
    expect(isQuizComplete({ 1: ans(true), 2: ans(false) }, [1, 2])).toBe(true);
    expect(isQuizComplete({ 1: ans(true) }, [1, 2])).toBe(false);
  });

  it("无题目不算完成", () => {
    expect(isQuizComplete({}, [])).toBe(false);
  });
});

describe("computeScore", () => {
  it("答完返回正确率", () => {
    expect(computeScore({ 1: ans(true), 2: ans(false) }, [1, 2])).toBe(0.5);
    expect(computeScore({ 1: ans(true), 2: ans(true) }, [1, 2])).toBe(1);
  });

  it("未答完返回 null", () => {
    expect(computeScore({ 1: ans(true) }, [1, 2])).toBeNull();
  });

  it("无题目返回 null", () => {
    expect(computeScore({}, [])).toBeNull();
  });
});

describe("wrongQuestions", () => {
  it("按题目顺序筛出答错的题", () => {
    const qs = [mkQ(1), mkQ(2), mkQ(3)];
    const answers = { 1: ans(true), 2: ans(false), 3: ans(false) };
    expect(wrongQuestions(qs, answers)).toEqual([qs[1], qs[2]]);
  });

  it("未作答的题不算错题", () => {
    const qs = [mkQ(1), mkQ(2)];
    expect(wrongQuestions(qs, { 1: ans(true) })).toEqual([]);
  });
});

describe("formatSourceSpan", () => {
  it("含页码与章节路径", () => {
    expect(formatSourceSpan({ page: 12, section_path: "第一章", text: "x" })).toBe(
      "第12页（第一章）",
    );
  });

  it("缺页码仍可显示章节路径", () => {
    expect(formatSourceSpan({ page: null, section_path: "第二章", text: "" })).toBe(
      "（第二章）",
    );
  });

  it("无页码无章节回退通用引用", () => {
    expect(formatSourceSpan({ page: null, section_path: "", text: "" })).toBe("参考课件");
  });

  it("null/undefined 安全", () => {
    expect(formatSourceSpan(null)).toBe("参考课件");
    expect(formatSourceSpan(undefined)).toBe("参考课件");
  });
});

describe("sourceExcerpt", () => {
  it("超长原文截断并加省略号", () => {
    const long = "字".repeat(200);
    const out = sourceExcerpt({ page: 1, section_path: "", text: long }, 10);
    expect(out).toBe("字".repeat(10) + "…");
  });

  it("短原文原样返回", () => {
    expect(sourceExcerpt({ page: 1, section_path: "", text: "短文本" })).toBe("短文本");
  });

  it("无原文返回空串", () => {
    expect(sourceExcerpt({ page: 1, section_path: "", text: "" })).toBe("");
    expect(sourceExcerpt(null)).toBe("");
  });
});
