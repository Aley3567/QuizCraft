/**
 * 后端 API client：上传/出题/答题三个端点的 fetch 封装 + 错误归一化。
 *
 * 仅包装 fetch，纯逻辑（baseUrl/请求体/错误解析）抽到独立函数并单测；
 * 网络调用本身在前端运行时验证，不在 vitest 覆盖（需 mock fetch，收益低）。
 */
import type {
  AnswerOut,
  DocumentDetail,
  DraftQuizGenerationRequest,
  QuestionOut,
  QuestionUpdateRequest,
  QuizGenerationRequest,
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
export async function generateQuiz(
  documentId: number,
  body?: QuizGenerationRequest,
): Promise<QuizGenerationResponse> {
  const init: RequestInit =
    body == null
      ? { method: "POST" }
      : {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(body),
        };
  const resp = await fetch(`${apiBaseUrl()}/api/documents/${documentId}/generate-quiz`, init);
  if (!resp.ok) throw await asApiError(resp);
  return (await resp.json()) as QuizGenerationResponse;
}

/** 生成草稿题：题目先留在 draft review，不进入 practice pool。 */
export function generateDraftQuiz(
  documentId: number,
  body?: DraftQuizGenerationRequest,
): Promise<QuizGenerationResponse> {
  return generateQuiz(documentId, { ...body, auto_publish: false });
}

/** 读取文档草稿题，供前端预览/编辑/发布。 */
export async function listDraftQuestions(documentId: number): Promise<QuestionOut[]> {
  const resp = await fetch(`${apiBaseUrl()}/api/documents/${documentId}/questions/drafts`, {
    method: "GET",
  });
  if (!resp.ok) throw await asApiError(resp);
  return (await resp.json()) as QuestionOut[];
}

/** 读取文档练习池题目：已发布且未标记坏题。 */
export async function listPracticeQuestions(documentId: number): Promise<QuestionOut[]> {
  const resp = await fetch(`${apiBaseUrl()}/api/documents/${documentId}/questions`, {
    method: "GET",
  });
  if (!resp.ok) throw await asApiError(resp);
  return (await resp.json()) as QuestionOut[];
}

/** 编辑题目草稿。 */
export async function updateQuestion(
  questionId: number,
  body: QuestionUpdateRequest,
): Promise<QuestionOut> {
  const resp = await fetch(`${apiBaseUrl()}/api/questions/${questionId}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw await asApiError(resp);
  return (await resp.json()) as QuestionOut;
}

/** 删除题目草稿。 */
export async function deleteQuestion(questionId: number): Promise<void> {
  const resp = await fetch(`${apiBaseUrl()}/api/questions/${questionId}`, {
    method: "DELETE",
  });
  if (!resp.ok) throw await asApiError(resp);
}

/** 发布草稿题，让它进入 practice pool。 */
export async function publishQuestion(questionId: number): Promise<QuestionOut> {
  const resp = await fetch(`${apiBaseUrl()}/api/questions/${questionId}/publish`, {
    method: "POST",
  });
  if (!resp.ok) throw await asApiError(resp);
  return (await resp.json()) as QuestionOut;
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
