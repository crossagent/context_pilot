#!/usr/bin/env python3
"""
Context Pilot A2A Streaming Client
===================================
与 context_pilot_agent 的 A2A API 进行流式交互。

用法:
    python call_a2a.py --query "你的任务"
"""

import argparse
import asyncio
import json
import sys
import uuid

import httpx


def parse_args():
    parser = argparse.ArgumentParser(description="Context Pilot A2A Streaming Client")
    parser.add_argument("--query", required=True, help="发送给 Agent 的任务描述（例如：查询某流程、记录新知识、更新错误经验）")
    parser.add_argument("--app-name", default="knowledge_app", help="ADK App 名称")
    parser.add_argument("--user-id", default="antigravity_user", help="用户 ID")
    return parser.parse_args()


async def create_session(base_url: str, app_name: str, user_id: str) -> str:
    """创建新 session，返回 session_id"""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{base_url}/apps/{app_name}/users/{user_id}/sessions",
            json={},
        )
        resp.raise_for_status()
        session_id = resp.json()["id"]
        print(f"✅ Session created: {session_id}", flush=True)
        return session_id


async def run_streaming(base_url: str, app_name: str, user_id: str, session_id: str, query: str):
    """通过 SSE 流式发送任务并实时打印事件。

    显示规则：
    - 💭 thought：每条单独一行，截断到 120 字
    - 💬 final text：同一 author 的连续 token 内联打印，切换 author/模式时换行
    - 🔧 tool_call / 📥 tool_resp：各自单行
    - 末尾的"完整摘要"重复事件自动跳过
    """
    """通过 SSE 流式发送任务并实时打印事件"""
    payload = {
        "app_name": app_name,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": query}],
        },
        "streaming": True,
    }

    event_count = 0
    # Track streaming display state to avoid repeated headers
    stream_author = None   # author currently being streamed inline
    stream_mode = None     # 'thought' | 'final' — current inline mode
    accumulated_final = "" # all final text printed so far (for duplicate detection)

    print(f"\n📤 Query: {query!r}\n{'─' * 60}", flush=True)

    async with httpx.AsyncClient(timeout=600) as client:
        async with client.stream("POST", f"{base_url}/run_sse", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue

                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"  [raw] {raw}", flush=True)
                    continue

                event_count += 1
                author = event.get("author", "?")
                content = event.get("content") or {}
                parts = content.get("parts") or []

                for part in parts:
                    thought = part.get("thought", False)

                    if "text" in part:
                        text = part["text"]

                        if thought:
                            # Thought: close any open inline stream, print on its own line
                            if stream_mode == "final":
                                print()  # close inline text line
                                stream_author = None
                                stream_mode = None
                            preview = text[:120].replace("\n", "↵")
                            print(f"\n  💭 [thought] [{author}] {preview}", flush=True)

                        else:
                            # Final text — detect duplicate "full summary" event sent at end.
                            # ADK sends all streaming deltas, then one final event with the
                            # complete response text. We detect it by prefix-matching:
                            # if we've printed 50+ chars already AND this new event's text
                            # STARTS WITH what we've already printed, it's the summary.
                            match_len = min(50, len(accumulated_final))
                            is_duplicate = (
                                match_len >= 50
                                and text.startswith(accumulated_final[:match_len])
                            )
                            if is_duplicate:
                                if stream_mode == "final":
                                    print()
                                    stream_author = None
                                    stream_mode = None
                                print(f"\n  ✂️  [summary event skipped]", flush=True)
                                continue

                            # Skip empty text events
                            if not text:
                                continue

                            # Detect final "complete response" summary event: ADK sends all
                            # streaming deltas, then one event containing the full response.
                            # It's reliably longer than or equal to everything accumulated.
                            is_summary = (
                                len(accumulated_final) >= 50
                                and len(text) >= len(accumulated_final)
                            )
                            if is_summary:
                                if stream_mode == "final":
                                    print()
                                    stream_author = None
                                    stream_mode = None
                                print(f"\n  📋 [recap — full response below]\n  {text}", flush=True)
                                continue
                            if stream_author != author or stream_mode != "final":
                                if stream_mode == "final":
                                    print()  # close previous author's inline line
                                print(f"\n  💬 [{author}] ", end="", flush=True)
                                stream_author = author
                                stream_mode = "final"

                            # Print text inline (no newline — tokens arrive in fragments)
                            print(text, end="", flush=True)
                            accumulated_final += text

                    elif "functionCall" in part:
                        # Close any open inline text stream
                        if stream_mode == "final":
                            print()
                            stream_author = None
                            stream_mode = None
                        fc = part["functionCall"]
                        args_preview = json.dumps(fc.get("args", {}), ensure_ascii=False)[:100]
                        print(
                            f"\n  🔧 [tool_call] [{author}] {fc.get('name')}({args_preview})",
                            flush=True,
                        )

                    elif "functionResponse" in part:
                        if stream_mode == "final":
                            print()
                            stream_author = None
                            stream_mode = None
                        fr = part["functionResponse"]
                        resp_preview = str(fr.get("response", ""))[:120].replace("\n", "↵")
                        print(
                            f"\n  📥 [tool_resp] [{author}] {fr.get('name')} → {resp_preview}",
                            flush=True,
                        )

                    else:
                        if stream_mode == "final":
                            print()
                            stream_author = None
                            stream_mode = None
                        print(f"  [event #{event_count:02d}] [{author}] (other part type)", flush=True)

    # Close final inline stream if still open
    if stream_mode == "final":
        print()

    print(f"\n{'─' * 60}", flush=True)
    print(f"✅ Total events: {event_count}", flush=True)

    if event_count > 1:
        print("🎉 Streaming OK — 收到多个中间事件", flush=True)
    elif event_count == 1:
        print("⚠️  仅收到 1 个事件 — 流式可能未正常工作", flush=True)
    else:
        print("❌ 未收到任何事件", flush=True)

    return accumulated_final


async def main():
    args = parse_args()
    base_url = "http://localhost:54090"

    print("=" * 60, flush=True)
    print(f"Context Pilot A2A Client", flush=True)
    print(f"Server : {base_url}", flush=True)
    print(f"App    : {args.app_name}", flush=True)
    print("=" * 60, flush=True)

    try:
        # 创建新 session
        session_id = await create_session(base_url, args.app_name, args.user_id)

        # 流式执行任务
        result = await run_streaming(base_url, args.app_name, args.user_id, session_id, args.query)

    except httpx.ConnectError as e:
        print(f"\n❌ 连接失败: {e}", flush=True)
        print(f"   请确认 knowledge_agent 已在 {base_url} 启动", flush=True)
        print(f"   启动命令: docker-compose up knowledge_expert", flush=True)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP 错误: {e.response.status_code} {e.response.text}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
