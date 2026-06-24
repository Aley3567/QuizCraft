"use client";

import { useState } from "react";
import { generateDraftQuiz } from "@/lib/api";
import { Uploader } from "@/components/Uploader";
import { DocumentSummary } from "@/components/DocumentSummary";
import { DraftReview } from "@/components/DraftReview";
import { QuizPlayer } from "@/components/QuizPlayer";
import { ResultView } from "@/components/ResultView";
import type { AnswerOut, DocumentDetail, QuizGenerationResponse } from "@/lib/types";

type Stage = "idle" | "uploaded" | "reviewing" | "quizzing" | "done";

/**
 * 切片 1.1 单页状态机：上传 → 出题 → 逐题答题（即时反馈）→ 结果 + 错题引用原文。
 * 后端默认 mock LLM，无需真实 key 即可跑通全链路（题面/反馈为 mock 内容）。
 */
export default function Page() {
  const [stage, setStage] = useState<Stage>("idle");
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [quiz, setQuiz] = useState<QuizGenerationResponse | null>(null);
  const [answers, setAnswers] = useState<Record<number, AnswerOut>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setStage("idle");
    setDoc(null);
    setQuiz(null);
    setAnswers({});
    setError(null);
    setBusy(false);
  }

  async function onGenerate() {
    if (!doc) return;
    setBusy(true);
    setError(null);
    try {
      const gen = await generateDraftQuiz(doc.id);
      setQuiz(gen);
      setAnswers({});
      setStage("reviewing");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="container">
      <h1>QuizCraft</h1>
      <p className="subtitle">上传课件 PDF，自动出选择题，错题反馈引用课件原文</p>

      {error && <p className="feedback err">{error}</p>}

      {stage === "idle" && (
        <Uploader
          onUploaded={(d) => {
            setDoc(d);
            setStage("uploaded");
          }}
        />
      )}

      {stage === "uploaded" && doc && (
        <>
          <DocumentSummary doc={doc} />
          <div className="card" style={{ display: "flex", gap: 12 }}>
            <button className="btn" disabled={busy} onClick={onGenerate}>
              {busy ? "出题中…" : "生成草稿题"}
            </button>
            <button className="btn btn-ghost" onClick={reset}>
              换一份
            </button>
          </div>
        </>
      )}

      {stage === "reviewing" && quiz && (
        <DraftReview
          initialDrafts={quiz.questions}
          onStartPractice={(questions) => {
            setQuiz({
              ...quiz,
              questions,
              quiz_session: {
                ...quiz.quiz_session,
                question_ids: questions.map((q) => q.id),
                total: questions.length,
              },
            });
            setAnswers({});
            setStage("quizzing");
          }}
        />
      )}

      {stage === "quizzing" && quiz && (
        <QuizPlayer
          questions={quiz.questions}
          sessionId={quiz.quiz_session.id}
          answers={answers}
          onAnswered={(qId, a) => setAnswers((prev) => ({ ...prev, [qId]: a }))}
          onFinish={() => setStage("done")}
        />
      )}

      {stage === "done" && quiz && (
        <ResultView questions={quiz.questions} answers={answers} onRestart={reset} />
      )}
    </main>
  );
}
