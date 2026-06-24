"use client";

import { useEffect, useState } from "react";
import { ApiError, listDueFlashcards, reviewFlashcard } from "@/lib/api";
import { formatSourceSpan, sourceExcerpt } from "@/lib/quiz-state";
import type { FlashcardOut, FlashcardReviewOut } from "@/lib/types";

const ratings = [
  { value: "again", label: "Again" },
  { value: "hard", label: "Hard" },
  { value: "good", label: "Good" },
  { value: "easy", label: "Easy" },
] as const;

function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.message : e instanceof Error ? e.message : String(e);
}

function nextDueText(review: FlashcardReviewOut): string {
  if (review.scheduled_days === 0) return "今天稍后";
  if (review.scheduled_days === 1) return "明天";
  return `${review.scheduled_days} 天后`;
}

export function FlashcardReview() {
  const [cards, setCards] = useState<FlashcardOut[]>([]);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [lastReview, setLastReview] = useState<FlashcardReviewOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    listDueFlashcards()
      .then((items) => {
        if (alive) {
          setCards(items);
          setIndex(0);
          setRevealed(false);
          setLastReview(null);
        }
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
  }, []);

  async function rateCurrent(rating: (typeof ratings)[number]["value"]) {
    const card = cards[index];
    if (!card) return;
    setSaving(true);
    setError(null);
    try {
      const reviewed = await reviewFlashcard(card.id, rating);
      setLastReview(reviewed);
      setCards((prev) => prev.filter((item) => item.id !== card.id));
      setIndex(0);
      setRevealed(false);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  const current = cards[index] ?? null;

  return (
    <div className="card review-session">
      <div className="review-head">
        <div>
          <h3>到期闪卡</h3>
          <p className="meta">
            {loading ? "正在读取..." : `${cards.length} 张待复习`}
          </p>
        </div>
        {current && <span className="status-dot">{current.state}</span>}
      </div>

      {error && <p className="feedback err">{error}</p>}
      {lastReview && (
        <p className="feedback ok">
          已记录，下一次复习：{nextDueText(lastReview)}
        </p>
      )}
      {!loading && !error && !current && (
        <p className="meta">当前没有到期闪卡。</p>
      )}
      {current && (
        <article className="review-card">
          <div className="progress">
            {index + 1} / {cards.length}
          </div>
          <h4>{current.front}</h4>
          {revealed ? (
            <>
              <p>{current.back}</p>
              <div className="source">
                来源：{formatSourceSpan(current.source_span)}
                {sourceExcerpt(current.source_span) && (
                  <div className="quote">{sourceExcerpt(current.source_span)}</div>
                )}
              </div>
              <div className="rating-row">
                {ratings.map((rating) => (
                  <button
                    key={rating.value}
                    className="btn btn-ghost"
                    disabled={saving}
                    onClick={() => rateCurrent(rating.value)}
                  >
                    {rating.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <button className="btn" onClick={() => setRevealed(true)}>
              显示背面
            </button>
          )}
        </article>
      )}
    </div>
  );
}
