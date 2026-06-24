"use client";

import { useEffect, useState } from "react";
import { ApiError, listFlashcards } from "@/lib/api";
import { formatSourceSpan, sourceExcerpt } from "@/lib/quiz-state";
import type { FlashcardOut } from "@/lib/types";

function originLabel(card: FlashcardOut): string {
  if (card.origin === "wrong_answer") return "错题卡";
  return "概念卡";
}

function priorityLabel(card: FlashcardOut): string {
  if (card.priority === "elevated") return "高优先级";
  return "普通";
}

function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.message : e instanceof Error ? e.message : String(e);
}

export function FlashcardList({ documentId }: { documentId: number }) {
  const [cards, setCards] = useState<FlashcardOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    listFlashcards({ documentId })
      .then((items) => {
        if (alive) setCards(items);
      })
      .catch((e) => {
        if (alive) setError(errorMessage(e));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [documentId]);

  return (
    <div className="card flashcards">
      <h3>闪卡复习池</h3>
      {loading && <p className="meta">正在读取闪卡...</p>}
      {error && <p className="feedback err">{error}</p>}
      {!loading && !error && cards.length === 0 && (
        <p className="meta">这份文档还没有生成闪卡。</p>
      )}
      {!loading && !error && cards.length > 0 && (
        <div className="flashcard-list">
          {cards.map((card) => (
            <article key={card.id} className="flashcard-item">
              <div className="progress">
                <span className="tag">{originLabel(card)}</span>
                <span className="tag">{priorityLabel(card)}</span>
              </div>
              <h4>{card.front}</h4>
              <p>{card.back}</p>
              <div className="source">
                来源：{formatSourceSpan(card.source_span)}
                {sourceExcerpt(card.source_span) && (
                  <div className="quote">{sourceExcerpt(card.source_span)}</div>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
