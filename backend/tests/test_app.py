"""FastAPI 应用层测试：应用可创建、健康检查端点可用。"""
from starlette.status import HTTP_200_OK


async def test_health_endpoint(client):
    """GET /health 返回 200 + 状态体。"""
    resp = await client.get("/health")
    assert resp.status_code == HTTP_200_OK
    body = resp.json()
    assert body["status"] == "ok"
