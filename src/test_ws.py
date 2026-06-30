import asyncio
import aiohttp
import sys
import json

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('http://localhost:8081/ws/chat?session_id=123') as ws:
            print("Connected")
            await ws.send_json({"type": "user_message", "payload": {"content": "Hello", "session_id": "123"}})
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    print("Received:", data)
                    if data.get("type") in ("message_complete", "error"):
                        break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

asyncio.run(main())
