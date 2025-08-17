"""
Simple LLM interface for OpenRouter.
"""

import json
import os
from typing import List, Optional

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult


class OpenRouterLLM(BaseChatModel):
    """Simple OpenRouter LLM implementation for LangGraph."""

    api_key: str = ""
    model: str = ""
    base_url: str = "https://openrouter.ai/api/v1"

    def __init__(
        self, api_key: Optional[str] = None, model: Optional[str] = None, **kwargs
    ):
        """Initialize OpenRouter LLM."""
        # Get values from env or parameters
        api_key_val = api_key or os.getenv("OPENROUTER_API_KEY", "")
        model_val = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1")

        # Call parent init with values
        super().__init__(api_key=api_key_val, model=model_val, **kwargs)

        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY env var."
            )

    def _generate(self, messages: List[BaseMessage], **kwargs) -> ChatResult:
        """Generate synchronously (required by base class)."""
        import asyncio

        return asyncio.run(self._agenerate(messages, **kwargs))

    async def _agenerate(self, messages: List[BaseMessage], **kwargs) -> ChatResult:
        """Generate response from OpenRouter."""
        # Convert messages to OpenRouter format
        openrouter_messages = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                openrouter_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                openrouter_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                message_dict = {"role": "assistant", "content": msg.content}
                # Handle tool calls if present
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    message_dict["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"]),
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                openrouter_messages.append(message_dict)
            elif isinstance(msg, ToolMessage):
                openrouter_messages.append(
                    {
                        "role": "tool",
                        "content": msg.content,
                        "tool_call_id": msg.tool_call_id,
                    }
                )

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/oracle-mcp-server",
            "X-Title": "Oracle MCP Chat Demo",
        }

        data = {
            "model": self.model,
            "messages": openrouter_messages,
            "temperature": kwargs.get("temperature", 0.7),
        }

        # Add tools if provided
        if "tools" in kwargs:
            data["tools"] = kwargs["tools"]

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                # Log the error details
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise
            result = response.json()

        # Extract response
        choice = result["choices"][0]
        message = choice["message"]

        # Create AIMessage with proper tool calls if present
        if "tool_calls" in message and message["tool_calls"]:
            ai_message = AIMessage(
                content=message.get("content", ""),
                tool_calls=[
                    {
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "args": json.loads(tc["function"]["arguments"]),
                    }
                    for tc in message["tool_calls"]
                ],
            )
        else:
            ai_message = AIMessage(content=message["content"])

        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    @property
    def _llm_type(self) -> str:
        """Return type of LLM."""
        return "openrouter"
