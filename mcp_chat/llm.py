"""
Simple OpenRouter LLM client using OpenAI SDK.
"""

import os
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI


class OpenRouterLLM:
    """Simple OpenRouter LLM client using OpenAI SDK."""

    def __init__(
        self, api_key: Optional[str] = None, model: Optional[str] = None, **kwargs
    ):
        """Initialize OpenRouter LLM."""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY env var."
            )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/oracle-mcp-server",
                "X-Title": "Oracle MCP Chat Demo",
            },
        )

    async def create_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a chat completion."""
        completion_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
        }

        if tools:
            completion_kwargs["tools"] = tools
            
        # Add tool_choice if provided
        if "tool_choice" in kwargs:
            completion_kwargs["tool_choice"] = kwargs["tool_choice"]

        response = await self.client.chat.completions.create(**completion_kwargs)
        return response.model_dump()
