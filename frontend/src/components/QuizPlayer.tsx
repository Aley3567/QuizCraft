"use client";

import { useState } from "react";
import { submitAnswer, ApiError } from "@/lib/api";
import { formatSourceSpan, sourceExcerpt } from "@/lib/quiz-state";
import type { AnswerOut, QuestionOut } from "@/lib/types";

/** 答题核心：一题一题答，选完即判分 + 引用原文反馈，确认后推进下一题。 */
export function QuizPlayer({
  questions,
  sessionId,
  answers,
  onAnswered,
  onFinish,
}: {
  questions: QuestionOut[];
  sessionId: number;
  answers: Record<number, AnswerOut>;
  onAnswered: (qId: number, ans: AnswerOut) => void;
  onFinish: () => void;
}) {
  const [viewIdx, setViewIdx] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const current = questions[viewIdx];
  if (!current) return null;
  const lastAnswer = answers[current.id] ?? null;
  const isLast = viewIdx === questions.length - 1;

  async function choose(optionIndex: number) {
    setError(null);
    setSubmitting(true);
    try {
      const ans = await submitAnswer(sessionId, current.id, optionIndex);
      onAnswered(current.id, ans);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : e instanceof Error ? e.message : String(e),
      );
    } finally {
      setSubmitting(false);
    }
  }

  function next() {
    if (isLast) {
      onFinish();
    } else {
      setViewIdx((i) => i + 1);
    }
  }

  return (
    <div className="card">
      <div className="progress">
        第 {viewIdx + 1} / {questions.length} 题
        {current.bloom_level && <span className="tag">{current.bloom_level}</span>}
        {current.difficulty && <span className="tag">{current.difficulty}</span>}
      </div>
      <div style={{ fontSize: 16 }}>{current.stem}</div>
      <div className="options">
        {current.options.map((opt, i) => (
          <button
            key={i}
            className={"option" + (lastAnswer?.selected_option_index === i ? " sel" : "")}
            disabled={submitting || lastAnswer != null}
            onClick={() => choose(i)}
          >
            {String.fromCharCode(65 + i)}. {opt}
          </button>
        ))}
      </div>

      {error && <p className="feedback err">{error}</p>}

      {lastAnswer && (
        <>
          <div className={"feedback " + (lastAnswer.is_correct ? "ok" : "err")}>
            {lastAnswer.feedback ||
              (lastAnswer.is_correct ? "回答正确。" : "回答错误。")}
          </div>
          <div className="source">
            来源：{formatSourceSpan(current.source_span)}
            {sourceExcerpt(current.source_span) && (
              <div className="quote">{sourceExcerpt(current.source_span)}</div>
            )}
          </div>
          <div style={{ marginTop: 12 }}>
            <button className="btn" onClick={next}>
              {isLast ? "查看结果" : "下一题"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
