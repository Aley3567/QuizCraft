"use client";

import type { DocumentDetail } from "@/lib/types";

/** 文档解析结果概览 + 分块明细（折叠）。 */
export function DocumentSummary({ doc }: { doc: DocumentDetail }) {
  return (
    <div className="card">
      <strong>{doc.filename}</strong>{" "}
      <span className="tag">{doc.status}</span>
      <div className="meta">
        {doc.page_count ?? "?"} 页 · {doc.section_count} 个结构分块
      </div>
      <details style={{ marginTop: 12 }}>
        <summary className="meta">查看解析出的分块（{doc.sections.length}）</summary>
        <div style={{ maxHeight: 240, overflow: "auto", marginTop: 8 }}>
          {doc.sections.map((s) => (
            <div key={s.id} className="source">
              第{s.page_number}页 · {s.section_path || "（无标题）"}
              <div className="quote">{s.content.slice(0, 120)}…</div>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
