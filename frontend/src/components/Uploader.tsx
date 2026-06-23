"use client";

import { useRef, useState } from "react";
import { uploadDocument } from "@/lib/api";
import type { DocumentDetail } from "@/lib/types";

/** PDF 拖拽/选择上传区，解析完成后回调父级。 */
export function Uploader({
  onUploaded,
}: {
  onUploaded: (doc: DocumentDetail) => void;
}) {
  const [drag, setDrag] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError(null);
    setLoading(true);
    try {
      const doc = await uploadDocument(file);
      onUploaded(doc);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div
        className={"dropzone" + (drag ? " drag" : "")}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <p>{loading ? "解析中…" : "拖拽 PDF 课件到这里，或点击选择文件"}</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
      </div>
      {error && <p className="feedback err">{error}</p>}
    </div>
  );
}
