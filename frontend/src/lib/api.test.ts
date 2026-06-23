import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { apiBaseUrl, buildAnswerBody, parseApiError } from "../lib/api";

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
  it("构造答题请求体", () => {
    expect(buildAnswerBody(7, 2)).toEqual({
      question_id: 7,
      selected_option_index: 2,
    });
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
