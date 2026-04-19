"""
Basic agent loop using the OpenAI Chat Completions API with tools.
Receives user input, calls tools as needed, and returns results.
"""

import json
import logging

from openai import OpenAI

from .config import OPENAI_API_KEY, DEFAULT_MODEL, LOG_LEVEL
from .tools import TOOLS, execute_tool

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an intelligent AI assistant.
You can use the provided tools to complete tasks.
Think step by step and use tools when necessary."""


def _openai_tool_definitions() -> list[dict]:
    """Build OpenAI Chat Completions `tools` list from TOOLS registry."""
    out: list[dict] = []
    for name, tool in TOOLS.items():
        props = {
            k: {"type": "string", "description": k}
            for k in tool["parameters"]
        }
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": list(tool["parameters"].keys()),
                    },
                },
            }
        )
    return out


def create_agent() -> OpenAI:
    """Create an agent with the OpenAI client."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured. Check your .env file")
    return OpenAI(api_key=OPENAI_API_KEY)


def run_agent_loop(client: OpenAI, user_input: str, max_turns: int = 10) -> str:
    """
    Run the agent loop: send message -> receive response -> call tool -> repeat.

    Args:
        client: OpenAI client
        user_input: User's question or request
        max_turns: Maximum number of tool-calling turns

    Returns:
        The agent's final response
    """
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    tools = _openai_tool_definitions()

    for turn in range(max_turns):
        logger.info("Turn %s/%s", turn + 1, max_turns)

        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=4096,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return (msg.content or "").strip()

        assistant_payload: dict = {
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in msg.tool_calls
            ],
        }
        messages.append(assistant_payload)

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            logger.info("Calling tool: %s(%s)", tc.function.name, args)
            result = execute_tool(tc.function.name, args)
            logger.info("Result: %s", result[:200])
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    return "Agent reached the maximum number of processing turns."


def main():
    """Interactive loop - enter a prompt and receive results."""
    client = create_agent()
    print("Agentic App (type 'quit' to exit)")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        try:
            response = run_agent_loop(client, user_input)
            print(f"\nAgent: {response}")
        except Exception as e:
            logger.error("Error: %s", e)
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
