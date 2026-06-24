"use client";

import { useMemo, useState } from "react";
import type { DocumentDetail, DraftQuizGenerationRequest } from "@/lib/types";

const DIFFICULTIES = [
  { value: "easy", label: "简单" },
  { value: "medium", label: "中等" },
  { value: "hard", label: "困难" },
];

const BLOOM_LEVELS = ["记忆", "理解", "应用", "分析"];

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

function evenDistribution(levels: string[]): Record<string, number> {
  const weight = 1 / levels.length;
  return Object.fromEntries(levels.map((level) => [level, weight]));
}

export function GenerationControls({
  doc,
  busy,
  onGenerate,
  onReset,
}: {
  doc: DocumentDetail;
  busy: boolean;
  onGenerate: (request: DraftQuizGenerationRequest) => void;
  onReset: () => void;
}) {
  const [questionCount, setQuestionCount] = useState(5);
  const [chapterScope, setChapterScope] = useState("");
  const [difficultyRange, setDifficultyRange] = useState(["easy", "medium"]);
  const [bloomLevels, setBloomLevels] = useState(["记忆", "理解"]);
  const [error, setError] = useState<string | null>(null);

  const sectionOptions = useMemo(() => {
    const paths = doc.sections.map((section) => section.section_path).filter(Boolean);
    return Array.from(new Set(paths));
  }, [doc.sections]);

  function submit() {
    if (!Number.isInteger(questionCount) || questionCount < 1) {
      setError("题数至少为 1。");
      return;
    }
    if (difficultyRange.length === 0) {
      setError("至少选择一个难度。");
      return;
    }
    if (bloomLevels.length === 0) {
      setError("至少选择一个 Bloom 层级。");
      return;
    }

    setError(null);
    onGenerate({
      number: questionCount,
      chapter_scope: chapterScope ? [chapterScope] : undefined,
      difficulty_range: difficultyRange,
      bloom_distribution: evenDistribution(bloomLevels),
    });
  }

  return (
    <div className="card controls">
      <div>
        <h2>生成设置</h2>
        <p className="meta">选择题数、章节范围、难度和 Bloom 层级后生成草稿题。</p>
      </div>

      {error && <p className="feedback err">{error}</p>}

      <div className="control-grid">
        <label className="field">
          题数
          <input
            type="number"
            min="1"
            max="50"
            value={questionCount}
            onChange={(e) => setQuestionCount(Number(e.target.value))}
          />
        </label>

        <label className="field">
          章节范围
          <select value={chapterScope} onChange={(e) => setChapterScope(e.target.value)}>
            <option value="">全部章节</option>
            {sectionOptions.map((sectionPath) => (
              <option key={sectionPath} value={sectionPath}>
                {sectionPath}
              </option>
            ))}
          </select>
        </label>
      </div>

      <fieldset className="choice-group">
        <legend>难度</legend>
        <div className="choice-row">
          {DIFFICULTIES.map((difficulty) => (
            <label className="check-pill" key={difficulty.value}>
              <input
                type="checkbox"
                checked={difficultyRange.includes(difficulty.value)}
                onChange={() =>
                  setDifficultyRange((prev) => toggleValue(prev, difficulty.value))
                }
              />
              {difficulty.label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="choice-group">
        <legend>Bloom 层级</legend>
        <div className="choice-row">
          {BLOOM_LEVELS.map((level) => (
            <label className="check-pill" key={level}>
              <input
                type="checkbox"
                checked={bloomLevels.includes(level)}
                onChange={() => setBloomLevels((prev) => toggleValue(prev, level))}
              />
              {level}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="actions">
        <button className="btn" disabled={busy} onClick={submit}>
          {busy ? "出题中..." : "生成草稿题"}
        </button>
        <button className="btn btn-ghost" onClick={onReset}>
          换一份
        </button>
      </div>
    </div>
  );
}
