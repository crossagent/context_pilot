"""
Manual A2A Streaming Verification Test
=======================================
验证 repo_explorer_agent (Provider) 与 context_pilot_agent (Consumer) 之间
的 A2A 流式通信是否正常工作。

前提条件
---------
1. 启动 Provider（repo_explorer_agent A2A server）：
       .\\start_repo_explorer_server.ps1
   或：
       uv run uvicorn context_pilot.context_pilot_app.remote_a2a.repo_explorer_agent.agent:app --port 8002 --reload

2. 确认 Agent Card 包含 streaming=True：
       curl http://localhost:8002/.well-known/agent.json

运行
----
    uv run python test/manual_a2a_streaming_test.py

预期输出
--------
- 多条 Event 按顺序打印（含 function_call / function_response）
- 中间事件 thought=True，最终事件 thought=None/False
"""

import asyncio
import httpx


ADK_API_BASE = "http://localhost:54089"
APP_NAME = "context_pilot_app"
USER_ID = "test_streaming_user"
QUERY = "请列出当前目录下所有 Python 文件（使用 rg 或 find）"


async def create_session() -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{ADK_API_BASE}/apps/{APP_NAME}/users/{USER_ID}/sessions",
            json={},
        )
        resp.raise_for_status()
        session_id = resp.json()["id"]
        print(f"✅ Session created: {session_id}")
        return session_id


async def run_streaming(session_id: str):
    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": QUERY}],
        },
        "streaming": True,
    }

    event_count = 0
    print(f"\n📤 Sending: {QUERY!r}\n{'─' * 60}")

    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream(
            "POST",
            f"{ADK_API_BASE}/run_sse",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue

                import json
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"  [raw] {raw}")
                    continue

                event_count += 1
                author = event.get("author", "?")
                content = event.get("content", {})
                parts = content.get("parts", [])

                for part in parts:
                    thought = part.get("thought", False)
                    tag = "💭 [thought]" if thought else "💬 [final]"

                    if "text" in part:
                        text_preview = part["text"][:120].replace("\n", "↵")
                        print(f"  Event #{event_count:02d} [ID:{event.get('id', 'N/A')}] {tag} author={author!r}")
                        print(f"    text: {text_preview}")

                    elif "functionCall" in part:
                        fc = part["functionCall"]
                        print(f"  Event #{event_count:02d} [ID:{event.get('id', 'N/A')}] {tag} author={author!r}")
                        print(f"    function_call: {fc.get('name')}({fc.get('args', {})})")

                    elif "functionResponse" in part:
                        fr = part["functionResponse"]
                        resp_preview = str(fr.get("response", ""))[:80]
                        print(f"  Event #{event_count:02d} [ID:{event.get('id', 'N/A')}] {tag} author={author!r}")
                        print(f"    function_response: {fr.get('name')} → {resp_preview}")

                    else:
                        print(f"  Event #{event_count:02d} {tag} author={author!r} [other part]")

    print(f"\n{'─' * 60}")
    print(f"✅ Total events received: {event_count}")
    if event_count > 1:
        print("🎉 Streaming is working! Multiple intermediate events received.")
    else:
        print("⚠️  Only 1 event received — streaming may not be enabled correctly.")


async def main():
    print("=" * 60)
    print("A2A Streaming Verification Test")
    print("Provider: repo_explorer_agent @ port 8002")
    print("Consumer: context_pilot_agent  @ port 8000")
    print("=" * 60)

    try:
        session_id = await create_session()
        await run_streaming(session_id)
    except httpx.ConnectError as e:
        print(f"\n❌ Connection failed: {e}")
        print("   Please ensure the Consumer (adk web/api_server) is running on port 8000")
        print("   and Provider (repo_explorer_agent) is running on port 8002.")


if __name__ == "__main__":
    asyncio.run(main())
