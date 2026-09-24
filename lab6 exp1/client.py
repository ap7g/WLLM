"""Expt 1 - MCP Client.
Connects to server.py, lets the user chat, and lets the LLM (Groq) decide which tool to call.

Setup:  pip install mcp groq
Run:    python client.py
"""
import asyncio
import json
import os
import sys

from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "openai/gpt-oss-120b"
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
SYSTEM = (
    "You are a personal assistant with a memory. If the user tells you something to remember, "
    "call save_note with the content and a few short tags. If the user asks about something "
    "they said before, call search_notes with keywords. Answer briefly."
)

GROQ_API_KEY = ""
client = Groq(api_key=GROQ_API_KEY)


async def main():
    sys.stdout.reconfigure(encoding="utf-8")  # so Windows console can print any character
    params = StdioServerParameters(command=sys.executable, args=[SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Convert MCP tool definitions to the function-calling format Groq expects
            mcp_tools = (await session.list_tools()).tools
            tools = [
                {"type": "function", "function": {
                    "name": t.name, "description": t.description, "parameters": t.input_schema,
                }}
                for t in mcp_tools
            ]
            print("Connected. Tools:", [t.name for t in mcp_tools])
            print("Type 'exit' to quit.\n")

            messages = [{"role": "system", "content": SYSTEM}]
            while True:
                query = input("You: ").strip()
                if query.lower() in ("exit", "quit"):
                    break
                if not query:
                    continue
                messages.append({"role": "user", "content": query})

                # Tool-use loop: keep going until the LLM stops asking for tools
                while True:
                    response = client.chat.completions.create(
                        model=MODEL, messages=messages, tools=tools, tool_choice="auto",
                    )
                    msg = response.choices[0].message

                    if not msg.tool_calls:
                        messages.append({"role": "assistant", "content": msg.content})
                        print(f"Assistant: {msg.content}\n")
                        break

                    messages.append({
                        "role": "assistant", "content": msg.content,
                        "tool_calls": [
                            {"id": tc.id, "type": "function",
                             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                            for tc in msg.tool_calls
                        ],
                    })
                    for tc in msg.tool_calls:
                        args = json.loads(tc.function.arguments or "{}")
                        print(f"  [LLM calls {tc.function.name}({args})]")
                        result = await session.call_tool(tc.function.name, args)
                        output = "".join(c.text for c in result.content if c.type == "text")
                        print(f"  [Server returned: {output[:200]}]")
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})


if __name__ == "__main__":
    asyncio.run(main())
