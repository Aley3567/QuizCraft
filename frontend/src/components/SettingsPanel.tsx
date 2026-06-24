"use client";

import { useEffect, useState } from "react";
import { ApiError, getLlmSettings, saveLlmSettings } from "@/lib/api";
import type { ConnectionResultOut, LlmConfigOut } from "@/lib/types";

function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.message : e instanceof Error ? e.message : String(e);
}

function configSummary(config: LlmConfigOut | null): string {
  if (!config) return "尚未配置";
  const keyState = config.has_api_key ? "已保存 key" : "未保存 key";
  const model = config.model ? ` · ${config.model}` : "";
  return `${config.provider}${model} · ${keyState}`;
}

export function SettingsPanel() {
  const [provider, setProvider] = useState("mock");
  const [model, setModel] = useState("gpt-4o");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [config, setConfig] = useState<LlmConfigOut | null>(null);
  const [connection, setConnection] = useState<ConnectionResultOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getLlmSettings()
      .then((saved) => {
        if (!active) return;
        setConfig(saved);
        setProvider(saved.provider);
        setModel(saved.model ?? "");
        setBaseUrl(saved.base_url ?? "");
      })
      .catch((e) => {
        if (!active) return;
        if (e instanceof ApiError && e.status === 404) return;
        setError(errorMessage(e));
      });
    return () => {
      active = false;
    };
  }, []);

  async function save() {
    setBusy(true);
    setError(null);
    setConnection(null);
    try {
      const result = await saveLlmSettings({
        provider,
        api_key: apiKey.trim() || undefined,
        model: model.trim() || undefined,
        base_url: baseUrl.trim() || undefined,
      });
      setConfig(result.config);
      setConnection(result.connection);
      setApiKey("");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card settings-panel" aria-label="LLM Settings">
      <div className="settings-head">
        <div>
          <h2>LLM 设置</h2>
          <p className="meta">{configSummary(config)}</p>
        </div>
        <span className={config?.has_api_key ? "status-dot ok-dot" : "status-dot"}>
          {config?.has_api_key ? "key 已保存" : "无 key"}
        </span>
      </div>

      {error && <p className="feedback err">{error}</p>}
      {connection && (
        <p className={connection.ok ? "feedback ok" : "feedback warn"}>
          {connection.ok ? "连接检查通过" : "连接检查未通过"}：{connection.message}
        </p>
      )}

      <div className="settings-grid">
        <label className="field">
          Provider
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="mock">mock</option>
            <option value="openai">openai-compatible</option>
          </select>
        </label>

        <label className="field">
          Model
          <input
            value={model}
            placeholder="gpt-4o"
            onChange={(e) => setModel(e.target.value)}
          />
        </label>

        <label className="field">
          API key
          <input
            type="password"
            value={apiKey}
            placeholder={config?.has_api_key ? "已保存，留空保持不显示" : "sk-..."}
            autoComplete="off"
            onChange={(e) => setApiKey(e.target.value)}
          />
        </label>

        <label className="field">
          Base URL
          <input
            value={baseUrl}
            placeholder="https://api.example.com/v1"
            onChange={(e) => setBaseUrl(e.target.value)}
          />
        </label>
      </div>

      <div className="actions">
        <button className="btn" disabled={busy} onClick={save}>
          {busy ? "保存中..." : "保存并测试连接"}
        </button>
      </div>
    </section>
  );
}
