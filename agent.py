#!/usr/bin/env python3
"""
Paris Events AI Agent (Gemini + Model Context Protocol / Luma MCP)

This agent connects to our Luma MCP server over stdio, discovers its tools dynamically,
and leverages Google Gemini to answer questions about events happening in Paris.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables (.env file)
load_dotenv()


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ Error: GEMINI_API_KEY is not set!")
        print("Please set your Gemini API key in a .env file:")
        print("  GEMINI_API_KEY=your_actual_key_here\n")
        sys.exit(1)
    return genai.Client(
        api_key=api_key,
        http_options={"api_version": "v1beta"}
    )


async def run_agent_turn(
    session: ClientSession,
    client: genai.Client,
    model_name: str,
    gemini_tool: types.Tool,
    conversation_history: list,
    user_prompt: str,
) -> str:
    """Runs one user turn with autonomous MCP tool execution loop."""
    print(f"\n👤 You: {user_prompt}")
    conversation_history.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
    )

    system_instruction = (
        "You are an energetic, knowledgeable AI concierge for events in Paris, France. "
        "You have direct access to Lu.ma (luma.com) events via the connected MCP tools. "
        "Always use the available MCP tools to look up real, live events in Paris whenever the user asks about "
        "events, meetups, hackathons, AI, tech, networking, or activities. "
        "Provide clear event names, dates, locations, links (URL), and ticket status (Free/Paid). "
        "You can respond in English or French depending on the user's language."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[gemini_tool],
        temperature=0.2,
    )

    while True:
        response = client.models.generate_content(
            model=model_name,
            contents=conversation_history,
            config=config,
        )

        candidate = response.candidates[0]
        model_content = candidate.content
        conversation_history.append(model_content)

        function_calls = response.function_calls
        if not function_calls:
            # Model has completed its response (no more tool calls)
            agent_text = response.text or ""
            print(f"\n🤖 Agent:\n{agent_text}\n")
            return agent_text

        # Process each tool call requested by Gemini
        tool_response_parts = []
        for call in function_calls:
            print(f"\n⚡ [MCP Tool Call] Gemini is calling '{call.name}' with arguments: {call.args}")
            try:
                mcp_res = await session.call_tool(call.name, call.args or {})
                tool_output_text = "\n".join(
                    c.text for c in mcp_res.content if hasattr(c, "text")
                )
            except Exception as e:
                tool_output_text = f"Error executing tool {call.name}: {str(e)}"

            print(f"📦 [MCP Tool Result] Received {len(tool_output_text)} characters from Luma MCP.")
            tool_response_parts.append(
                types.Part.from_function_response(
                    name=call.name,
                    response={"result": tool_output_text},
                )
            )

        # Append tool execution results to conversation history and loop back to model
        conversation_history.append(
            types.Content(role="user", parts=tool_response_parts)
        )


async def main():
    gemini_client = get_gemini_client()
    model_name = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    # Path to Luma MCP Server
    server_script = os.path.join(os.path.dirname(__file__), "luma_mcp_server.py")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=os.environ.copy(),
    )

    print("==================================================")
    print("🗼 Paris Events AI Agent (Gemini + Luma MCP)")
    print("==================================================")
    print("Connecting to Luma MCP Server via stdio...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_list = await session.list_tools()
            tool_names = [t.name for t in tools_list.tools]
            print(f"✅ Connected to MCP Server! Discovered tools: {tool_names}")

            # Convert MCP tool definitions into Gemini FunctionDeclaration format
            gemini_function_declarations = []
            for tool in tools_list.tools:
                decl = types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=tool.input_schema,
                )
                gemini_function_declarations.append(decl)

            gemini_tool = types.Tool(function_declarations=gemini_function_declarations)

            conversation_history = []

            # Check if a prompt was provided via command line arguments
            if len(sys.argv) > 1:
                initial_query = " ".join(sys.argv[1:])
                await run_agent_turn(
                    session,
                    gemini_client,
                    model_name,
                    gemini_tool,
                    conversation_history,
                    initial_query,
                )
                return

            print("\nType your question about Paris events (e.g. 'What tech and AI events are happening in Paris this week?')")
            print("Type 'exit' or 'quit' to stop.\n")

            while True:
                try:
                    user_input = input("You > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nAu revoir!")
                    break

                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("\nAu revoir!")
                    break

                await run_agent_turn(
                    session,
                    gemini_client,
                    model_name,
                    gemini_tool,
                    conversation_history,
                    user_input,
                )


if __name__ == "__main__":
    asyncio.run(main())
