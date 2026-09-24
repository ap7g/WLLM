"""Expt 2 - Weather Dashboard (MCP client + Streamlit UI).
Shows the LLM's thought process: its reasoning, the decision to call the tool, the raw data, and the final answer.

Setup:  pip install mcp groq streamlit
Run:    streamlit run app.py
"""
import asyncio
import json
import os
import sys

import streamlit as st
from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "openai/gpt-oss-120b"
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
SYSTEM = (
    "You are a weather assistant. Use get_current_weather to fetch live data, "
    "then give a short, friendly summary with the key numbers."
)

GROQ_API_KEY = ""
client = Groq(api_key=GROQ_API_KEY)


async def ask(question, status):
    params = StdioServerParameters(command=sys.executable, args=[SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = (await session.list_tools()).tools
            tools = [
                {"type": "function", "function": {
                    "name": t.name, "description": t.description, "parameters": t.input_schema,
                }}
                for t in mcp_tools
            ]
            status.write(f"🔌 Connected to MCP server. Tools: `{[t.name for t in mcp_tools]}`")

            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": question},
            ]
            while True:
                status.write("🧠 Sending question and available tools to the LLM...")
                response = client.chat.completions.create(
                    model=MODEL, messages=messages, tools=tools, tool_choice="auto",
                )
                msg = response.choices[0].message
                if getattr(msg, "reasoning", None):
                    status.markdown(f"💭 **LLM reasoning:** {msg.reasoning}")

                if not msg.tool_calls:
                    status.write("✅ LLM has enough data and is writing the final answer.")
                    return msg.content

                if msg.content:
                    status.markdown(f"💭 **LLM:** {msg.content}")
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
                    status.markdown(f"🛠️ **LLM decided to call:** `{tc.function.name}({args})`")
                    result = await session.call_tool(tc.function.name, args)
                    output = "".join(c.text for c in result.content if c.type == "text")
                    status.markdown("📦 **Data returned by server:**")
                    status.code(output)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})


st.set_page_config(page_title="Weather Dashboard", page_icon="🌦️")
st.title("🌦️ AI Weather Dashboard")
st.caption("MCP client ↔ weather MCP server (wttr.in) ↔ Groq LLM")

question = st.chat_input("Ask about the weather, e.g. What's the weather in Tokyo?")
if question:
    st.chat_message("user").write(question)
    with st.chat_message("assistant"):
        with st.status("LLM thought process", expanded=True) as status:
            answer = asyncio.run(ask(question, status))
            status.update(label="LLM thought process (done)", state="complete")
        st.markdown(answer)
