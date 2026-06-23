"use client";

import { computeScore, formatSourceSpan, sourceExcerpt, wrongQuestions } from "@/lib/quiz-state";
import type { AnswerMap } from "@/lib/quiz-state";
import type { QuestionOut } from "@/lib/types";

/** 答题结束：总分 + 错题列表（每题引用文档原文/页码）。 */
export function ResultView({
  questions,
  answers,
  onRestart,
}: {
  questions: QuestionOut[];
  answers: AnswerMap;
  onRestart: () => void;
}) {
  const ids = questions.map((q) => q.id);
  const score = computeScore(answers, ids);
  const correctCount = ids.filter((id) => answers[id]?.is_correct === true).length;
  const wrongs = wrongQuestions(questions, answers);

  return (
    <div>
      <div className="card">
        <div className="score">
          {score != null
            ? `正确 ${correctCount} / ${ids.length}（${Math.round(score * 100)}%）`
            : "未完成答题"}
        </div>
      </div>

      {wrongs.length > 0 ? (
        <div className="card err-list">
          <h3>错题反馈（{wrongs.length}）</h3>
          {wrongs.map((q) => {
            const a = answers[q.id];
            const selected = a?.selected_option_index;
            return (
              <div key={q.id} className="feedback err">
                <div>{q.stem}</div>
                {selected != null && (
                  <div className="muted">你的选择：{String.fromCharCode(65 + selected)}. {q.options[selected]}</div>
                )}
                <div style={{ marginTop: 8 }}>{a?.feedback || "（无反馈）"}</div>
                <div className="source">
                  来源：{formatSourceSpan(q.source_span)}
                  {sourceExcerpt(q.source_span) && (
                    <div className="quote">{sourceExcerpt(q.source_span)}</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card">
          <p>全部答对，没有错题。</p>
        </div>
      )}

      <div className="card" style={{ display: "flex", gap: 12 }}>
        <button className="btn" onClick={onRestart}>
          再上传一份
        </button>
      </div>
    </div>
  );
}
