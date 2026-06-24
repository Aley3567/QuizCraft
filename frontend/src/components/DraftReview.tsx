"use client";

import { useState } from "react";
import {
  ApiError,
  deleteQuestion,
  publishQuestion,
  updateQuestion,
} from "@/lib/api";
import { formatSourceSpan, sourceExcerpt } from "@/lib/quiz-state";
import type { QuestionOut } from "@/lib/types";

type DraftForm = {
  stem: string;
  optionsText: string;
  correctOptionIndex: string;
  answerText: string;
  explanation: string;
};

function formFromQuestion(q: QuestionOut): DraftForm {
  return {
    stem: q.stem,
    optionsText: q.options.join("\n"),
    correctOptionIndex: q.correct_option_index != null ? String(q.correct_option_index) : "",
    answerText: q.answer_text ?? "",
    explanation: q.explanation ?? "",
  };
}

function questionTypeLabel(type: string): string {
  if (type === "multiple_choice") return "选择题";
  if (type === "short_answer") return "简答题";
  if (type === "fill_blank") return "填空题";
  return type;
}

export function DraftReview({
  initialDrafts,
  onStartPractice,
}: {
  initialDrafts: QuestionOut[];
  onStartPractice: (questions: QuestionOut[]) => void;
}) {
  const [drafts, setDrafts] = useState(initialDrafts);
  const [published, setPublished] = useState<QuestionOut[]>([]);
  const [forms, setForms] = useState<Record<number, DraftForm>>(
    Object.fromEntries(initialDrafts.map((q) => [q.id, formFromQuestion(q)])),
  );
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function setForm(id: number, patch: Partial<DraftForm>) {
    setForms((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));
  }

  function errorMessage(e: unknown): string {
    return e instanceof ApiError ? e.message : e instanceof Error ? e.message : String(e);
  }

  async function save(q: QuestionOut) {
    const form = forms[q.id] ?? formFromQuestion(q);
    setBusyId(q.id);
    setError(null);
    try {
      const payload =
        q.question_type === "multiple_choice" || q.question_type === "fill_blank"
          ? {
              stem: form.stem,
              options: form.optionsText
                .split("\n")
                .map((s) => s.trim())
                .filter(Boolean),
              correct_option_index:
                form.correctOptionIndex === ""
                  ? undefined
                  : Number(form.correctOptionIndex),
              explanation: form.explanation,
            }
          : {
              stem: form.stem,
              answer_text: form.answerText,
              explanation: form.explanation,
            };
      const updated = await updateQuestion(q.id, payload);
      setDrafts((prev) => prev.map((item) => (item.id === q.id ? updated : item)));
      setForms((prev) => ({ ...prev, [q.id]: formFromQuestion(updated) }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(q: QuestionOut) {
    setBusyId(q.id);
    setError(null);
    try {
      await deleteQuestion(q.id);
      setDrafts((prev) => prev.filter((item) => item.id !== q.id));
      setForms((prev) => {
        const next = { ...prev };
        delete next[q.id];
        return next;
      });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusyId(null);
    }
  }

  async function publish(q: QuestionOut) {
    setBusyId(q.id);
    setError(null);
    try {
      const next = await publishQuestion(q.id);
      setDrafts((prev) => prev.filter((item) => item.id !== q.id));
      setPublished((prev) => [...prev, next]);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="card">
        <h2>审核草稿题</h2>
        <p className="meta">
          草稿题发布前不会进入练习池。逐题保存、删除或发布后再开始练习。
        </p>
        {error && <p className="feedback err">{error}</p>}
      </div>

      {drafts.map((q) => {
        const form = forms[q.id] ?? formFromQuestion(q);
        const busy = busyId === q.id;
        const isObjective =
          q.question_type === "multiple_choice" || q.question_type === "fill_blank";
        return (
          <div className="card" key={q.id}>
            <div className="progress">
              <span className="tag">{questionTypeLabel(q.question_type)}</span>
              {q.bloom_level && <span className="tag">{q.bloom_level}</span>}
              {q.difficulty && <span className="tag">{q.difficulty}</span>}
            </div>

            <label className="field">
              题干
              <textarea
                value={form.stem}
                onChange={(e) => setForm(q.id, { stem: e.target.value })}
              />
            </label>

            {isObjective ? (
              <>
                <label className="field">
                  选项（每行一个）
                  <textarea
                    value={form.optionsText}
                    onChange={(e) => setForm(q.id, { optionsText: e.target.value })}
                  />
                </label>
                <label className="field">
                  正确答案下标
                  <input
                    type="number"
                    min="0"
                    value={form.correctOptionIndex}
                    onChange={(e) =>
                      setForm(q.id, { correctOptionIndex: e.target.value })
                    }
                  />
                </label>
              </>
            ) : (
              <label className="field">
                参考答案
                <textarea
                  value={form.answerText}
                  onChange={(e) => setForm(q.id, { answerText: e.target.value })}
                />
              </label>
            )}

            <label className="field">
              解析
              <textarea
                value={form.explanation}
                onChange={(e) => setForm(q.id, { explanation: e.target.value })}
              />
            </label>

            <div className="source">
              来源：{formatSourceSpan(q.source_span)}
              {sourceExcerpt(q.source_span) && (
                <div className="quote">{sourceExcerpt(q.source_span)}</div>
              )}
            </div>

            <div className="actions">
              <button className="btn" disabled={busy} onClick={() => save(q)}>
                保存
              </button>
              <button className="btn btn-ghost" disabled={busy} onClick={() => publish(q)}>
                发布
              </button>
              <button className="btn btn-danger" disabled={busy} onClick={() => remove(q)}>
                删除
              </button>
            </div>
          </div>
        );
      })}

      {drafts.length === 0 && (
        <div className="card">
          <p className="meta">没有待审核草稿。</p>
          {published.length > 0 && (
            <button className="btn" onClick={() => onStartPractice(published)}>
              开始练习
            </button>
          )}
        </div>
      )}
    </div>
  );
}
