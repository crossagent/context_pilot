import asyncio
import os
import httpx

TARGET_ENV = os.getenv("TARGET_ENV", "windows")
ADK_API_BASE = "http://localhost:54089" if TARGET_ENV == "docker" else "http://localhost:8000"
APP_NAME = "context_pilot_app"
USER_ID = "test_streaming_user"
QUERY = "你好，请简单做个自我介绍（不要调用知识库）。"

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

    print(f"\n{'─' * 60}")
    print(f"✅ Total events received: {event_count}")

async def main():
    print("=" * 60)
    print("Test 1: Main Agent Independent Streaming")
    print(f"Target: {ADK_API_BASE} (App: {APP_NAME})")
    print("=" * 60)
    try:
        session_id = await create_session()
        await run_streaming(session_id)
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
