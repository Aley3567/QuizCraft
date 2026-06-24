import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  apiBaseUrl,
  buildAnswerBody,
  deleteQuestion,
  generateDraftQuiz,
  getLlmSettings,
  listDraftQuestions,
  parseApiError,
  publishQuestion,
  saveLlmSettings,
  submitAnswer,
  updateQuestion,
} from "../lib/api";

const question = {
  id: 7,
  concept_id: null,
  section_id: 3,
  question_type: "multiple_choice",
  stem: "原题干",
  options: ["A", "B"],
  correct_option_index: 0,
  answer_text: null,
  explanation: "解析",
  source_span: { page: 12, section_path: "第一章", text: "原文" },
  bloom_level: "记忆",
  difficulty: "easy",
  self_eval_score: null,
  is_flagged: false,
  in_practice_pool: false,
};

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    status: init?.status ?? 200,
    headers: { "content-type": "application/json" },
  });
}

describe("apiBaseUrl", () => {
  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  });

  it("默认指向本机后端 :8000", () => {
    expect(apiBaseUrl()).toBe("http://localhost:8000");
  });

  it("环境变量覆盖", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.example";
    expect(apiBaseUrl()).toBe("http://api.example");
  });
});

describe("buildAnswerBody", () => {
  it("构造选择题答题请求体", () => {
    expect(buildAnswerBody(7, 2)).toEqual({
      question_id: 7,
      selected_option_index: 2,
    });
  });

  it("构造填空/简答题文本答题请求体", () => {
    expect(buildAnswerBody(8, { text: "类囊体膜" })).toEqual({
      question_id: 8,
      short_answer_text: "类囊体膜",
    });
  });
});

describe("draft review API", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("生成草稿时传 auto_publish=false，使题先留在草稿池", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        quiz_session: {
          id: 1,
          document_id: 5,
          question_ids: [7],
          status: "in_progress",
          score: null,
          total: 1,
          created_at: null,
        },
        questions: [question],
        concepts: [],
      }),
    );

    const result = await generateDraftQuiz(5);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/documents/5/generate-quiz",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ auto_publish: false }),
      },
    );
    expect(result.questions[0].in_practice_pool).toBe(false);
  });

  it("生成草稿时把题数、章节、难度和 Bloom 参数传给后端", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        quiz_session: {
          id: 1,
          document_id: 5,
          question_ids: [7],
          status: "in_progress",
          score: null,
          total: 1,
          created_at: null,
        },
        questions: [question],
        concepts: [],
      }),
    );

    await generateDraftQuiz(5, {
      number: 3,
      chapter_scope: ["第2章 光合作用"],
      difficulty_range: ["easy"],
      bloom_distribution: { 记忆: 0.5, 应用: 0.5 },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/documents/5/generate-quiz",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          number: 3,
          chapter_scope: ["第2章 光合作用"],
          difficulty_range: ["easy"],
          bloom_distribution: { 记忆: 0.5, 应用: 0.5 },
          auto_publish: false,
        }),
      },
    );
  });

  it("读取草稿题列表用于预览", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(jsonResponse([question]));

    await expect(listDraftQuestions(5)).resolves.toEqual([question]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/documents/5/questions/drafts",
      { method: "GET" },
    );
  });

  it("编辑草稿题干和答案字段后返回持久化后的题目", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ ...question, stem: "新题干", correct_option_index: 1 }),
    );

    const updated = await updateQuestion(7, {
      stem: "新题干",
      correct_option_index: 1,
    });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/questions/7", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ stem: "新题干", correct_option_index: 1 }),
    });
    expect(updated.stem).toBe("新题干");
    expect(updated.correct_option_index).toBe(1);
  });

  it("发布草稿后题目进入练习池", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(jsonResponse({ ...question, in_practice_pool: true }));

    const published = await publishQuestion(7);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/questions/7/publish",
      { method: "POST" },
    );
    expect(published.in_practice_pool).toBe(true);
  });

  it("删除草稿使用后端删除端点", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await deleteQuestion(7);

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/questions/7", {
      method: "DELETE",
    });
  });
});

describe("settings API", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("保存 LLM 配置时返回脱敏状态，不把明文 key 暴露给调用方", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        config: {
          provider: "openai",
          has_api_key: true,
          model: "gpt-4o",
          base_url: "https://api.example.com/v1",
        },
        connection: {
          ok: false,
          provider: "openai",
          model: "gpt-4o",
          message: "connection refused",
        },
      }),
    );

    const saved = await saveLlmSettings({
      provider: "openai",
      api_key: "sk-never-return",
      model: "gpt-4o",
      base_url: "https://api.example.com/v1",
    });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/settings/llm", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        provider: "openai",
        api_key: "sk-never-return",
        model: "gpt-4o",
        base_url: "https://api.example.com/v1",
      }),
    });
    expect(saved.config.has_api_key).toBe(true);
    expect("api_key" in saved.config).toBe(false);
    expect(JSON.stringify(saved)).not.toContain("sk-never-return");
    expect(saved.connection.ok).toBe(false);
    expect(saved.connection.message).toBe("connection refused");
  });

  it("读取 LLM 配置只返回 has_api_key 脱敏状态", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        provider: "mock",
        has_api_key: true,
        model: "mock-model",
        base_url: null,
      }),
    );

    const config = await getLlmSettings();

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/settings/llm", {
      method: "GET",
    });
    expect(config.has_api_key).toBe(true);
    expect("api_key" in config).toBe(false);
  });
});

describe("answer API", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("提交填空/简答文本答案到公开答题端点", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        id: 3,
        quiz_session_id: 2,
        question_id: 8,
        selected_option_index: null,
        short_answer_text: "类囊体膜",
        is_correct: true,
        score: null,
        feedback: "课件第12页提到类囊体膜。",
      }),
    );

    const result = await submitAnswer(2, 8, { text: "类囊体膜" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/quiz-sessions/2/answer",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          question_id: 8,
          short_answer_text: "类囊体膜",
        }),
      },
    );
    expect(result.short_answer_text).toBe("类囊体膜");
  });
});

describe("parseApiError", () => {
  it("提取字符串 detail", () => {
    expect(parseApiError(404, { detail: "文档不存在" })).toBe("文档不存在");
  });

  it("detail 为对象时 JSON 序列化（FastAPI 校验错误）", () => {
    expect(parseApiError(422, { detail: [{ loc: ["body"], msg: "bad" }] })).toBe(
      JSON.stringify([{ loc: ["body"], msg: "bad" }]),
    );
  });

  it("无 detail 时回退状态码描述", () => {
    expect(parseApiError(500, {})).toBe("请求失败（HTTP 500）");
  });

  it("body 为 null 时回退", () => {
    expect(parseApiError(502, null)).toBe("请求失败（HTTP 502）");
  });
});
