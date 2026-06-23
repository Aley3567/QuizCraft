"""CORS 中间件测试：前端（Next.js dev server :3000）跨域调用后端必需。

切片 1.1 前端子系统接入前先打通跨域，否则浏览器预检会拦掉所有跨源请求。
"""
import pytest


@pytest.mark.asyncio
async def test_cors_preflight_allows_frontend_origin(client):
    """OPTIONS 预检从前端源发起应返回 200 + 允许跨域头。"""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    resp = await client.options("/api/documents", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in resp.headers["access-control-allow-methods"]


@pytest.mark.asyncio
async def test_cors_actual_request_has_allow_origin(client):
    """带 Origin 的实际请求响应应回写 Access-Control-Allow-Origin。"""
    resp = await client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_disallows_unknown_origin_by_default(client):
    """未配置的源不应被回写为允许源（默认仅放行前端开发源）。"""
    resp = await client.get("/health", headers={"Origin": "http://evil.example"})
    assert resp.status_code == 200  # 简单 GET 仍放行，但不应声明该源为允许源
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example"
