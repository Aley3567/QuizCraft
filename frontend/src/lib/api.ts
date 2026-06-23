/**
 * 后端 API client：上传/出题/答题三个端点的 fetch 封装 + 错误归一化。
 *
 * 仅包装 fetch，纯逻辑（baseUrl/请求体/错误解析）抽到独立函数并单测；
 * 网络调用本身在前端运行时验证，不在 vitest 覆盖（需 mock fetch，收益低）。
 */
import type {
  AnswerOut,
  DocumentDetail,
  QuizGenerationResponse,
} from "./types";

/** 后端 API 基址，默认本机 FastAPI dev server（:8000）。 */
export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

/** 归一化后端错误：FastAPI 4xx/5xx body 多为 {detail: ...}。 */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** 把后端 4xx/5xx 响应体转成可读消息。 */
export function parseApiError(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    return JSON.stringify(detail);
  }
  return `请求失败（HTTP ${status}）`;
}

async function asApiError(resp: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await resp.json();
  } catch {
    body = null;
  }
  return new ApiError(resp.status, parseApiError(resp.status, body));
}

/** 上传 PDF，返回文档详情（含解析出的结构分块）。 */
export async function uploadDocument(file: File): Promise<DocumentDetail> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${apiBaseUrl()}/api/documents`, {
    method: "POST",
    body: form,
  });
  if (!resp.ok) throw await asApiError(resp);
  return (await resp.json()) as DocumentDetail;
}

/** 出题：对文档执行两步生成，返回答题会话 + 题目 + 概念。 */
export async function generateQuiz(documentId: number): Promise<QuizGenerationResponse> {
  const resp = await fetch(
    `${apiBaseUrl()}/api/documents/${documentId}/generate-quiz`,
    { method: "POST" },
  );
  if (!resp.ok) throw await asApiError(resp);
  return (await resp.json()) as QuizGenerationResponse;
}

/** 构造答题请求体（与后端 AnswerRequest 对齐）。 */
export function buildAnswerBody(questionId: number, selectedOptionIndex: number) {
  return { question_id: questionId, selected_option_index: selectedOptionIndex };
}

/** 提交单题作答，返回判分结果 + 引用原文的 LLM 反馈。 */
export async function submitAnswer(
  sessionId: number,
  questionId: number,
  selectedOptionIndex: number,
): Promise<AnswerOut> {
  const resp = await fetch(`${apiBaseUrl()}/api/quiz-sessions/${sessionId}/answer`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(buildAnswerBody(questionId, selectedOptionIndex)),
  });
  if (!resp.ok) throw await asApiError(resp);
  return (await resp.json()) as AnswerOut;
}
