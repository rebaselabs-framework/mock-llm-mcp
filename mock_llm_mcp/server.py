"""
Mock LLM MCP Server v1.0.0

Exposes Mock LLM API as MCP tools for AI agents.
Agents can mock OpenAI, Anthropic, and Google Gemini API calls — no real keys needed.

Use cases:
  - Test LLM integration code without spending tokens
  - Simulate error conditions (rate limits, server errors, invalid keys)
  - Deterministic responses for CI/CD pipelines
  - Frontend development without real API keys

Usage:
    pip install mock-llm-mcp
    # Then configure in Claude Desktop or any MCP-compatible host:
    # {
    #   "mcpServers": {
    #     "mock-llm": {
    #       "command": "uvx",
    #       "args": ["mock-llm-mcp"],
    #       "env": {"MOCK_LLM_API_KEY": "your-key-here"}
    #     }
    #   }
    # }
    #
    # No API key required for basic usage — Mock LLM API has a free tier.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
API_BASE = os.environ.get("MOCK_LLM_API_URL", "https://mock-llm-api.rebaselabs.online")
API_KEY = os.environ.get("MOCK_LLM_API_KEY", "")
DEFAULT_TIMEOUT = 30.0

mcp = FastMCP(
    "mock-llm",
    instructions=(
        "Mock LLM gives you drop-in mock responses for OpenAI, Anthropic, and Google Gemini APIs. "
        "Use it to test LLM integration code, simulate errors, and run offline CI pipelines — "
        "without spending real API tokens. Set MOCK_LLM_API_KEY for authenticated access (higher limits). "
        "Available at https://mock-llm-api.rebaselabs.online"
    ),
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _headers(provider: str = "openai") -> dict[str, str]:
    """Build headers — API key optional for free tier."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


async def _post(path: str, body: dict, extra_headers: dict | None = None) -> dict:
    headers = _headers()
    if extra_headers:
        headers.update(extra_headers)
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.post(f"{API_BASE}{path}", json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def _get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.get(f"{API_BASE}{path}", headers=_headers())
        resp.raise_for_status()
        return resp.json()


def _mock_headers(
    length: str,
    response_type: str,
    error: str,
    delay_ms: int,
    seed: int | None,
) -> dict[str, str]:
    """Build x-mock-* control headers."""
    headers: dict[str, str] = {}
    if length != "medium":
        headers["x-mock-length"] = length
    if response_type != "auto":
        headers["x-mock-type"] = response_type
    if error != "none":
        headers["x-mock-error"] = error
    if delay_ms > 0:
        headers["x-mock-delay"] = str(delay_ms)
    if seed is not None:
        headers["x-mock-seed"] = str(seed)
    return headers


def _extract_text(response: dict) -> str:
    """Extract readable text from various response shapes."""
    # OpenAI format
    if "choices" in response:
        choices = response["choices"]
        if choices and "message" in choices[0]:
            return choices[0]["message"].get("content", "")
        if choices and "text" in choices[0]:
            return choices[0]["text"]
    # Anthropic format
    if "content" in response:
        content = response["content"]
        if isinstance(content, list) and content:
            return content[0].get("text", "")
        if isinstance(content, str):
            return content
    # Google format
    if "candidates" in response:
        candidates = response["candidates"]
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                return parts[0].get("text", "")
    # Mock /mock endpoint
    if "content" in response:
        return response["content"]
    return json.dumps(response, indent=2)


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def mock_quick(
    prompt: str,
    length: str = "medium",
    response_type: str = "auto",
    seed: Optional[int] = None,
) -> str:
    """
    Quickest way to get a mock LLM response — provider-agnostic.
    No need to format a full OpenAI/Anthropic request body.

    Response type is inferred from your prompt unless you specify it.
    Great for rapid prototyping and sanity-checking integrations.

    Args:
        prompt: The prompt text (used for type inference and response generation)
        length: Response length — "short", "medium" (default), "long", "xl", or "random"
        response_type: "text" (default: auto-detect), "code", "json", "markdown", or "list"
        seed: Integer seed for deterministic/reproducible responses
    """
    body: dict[str, Any] = {"prompt": prompt, "length": length, "type": response_type}
    if seed is not None:
        body["seed"] = seed
    result = await _post("/mock", body)
    content = result.get("content", str(result))
    meta = f"\n\n[type={result.get('type', '?')} | length={result.get('length', '?')} | ~{result.get('tokens', '?')} tokens]"
    return content + meta


@mcp.tool()
async def mock_openai_chat(
    messages: list[dict],
    model: str = "gpt-4o",
    length: str = "medium",
    response_type: str = "auto",
    error: str = "none",
    delay_ms: int = 0,
    seed: Optional[int] = None,
) -> str:
    """
    Mock an OpenAI chat completions response (POST /v1/chat/completions).
    Returns a response in exactly the OpenAI API format — drop-in compatible.

    Use this to test code that calls `openai.chat.completions.create(...)` without
    spending real tokens or needing an API key.

    Args:
        messages: List of message dicts [{"role": "user", "content": "..."}]
        model: Model name to appear in response (default: "gpt-4o")
        length: Response length — "short", "medium", "long", "xl", "random"
        response_type: "auto", "text", "code", "json", "markdown", "list"
        error: Simulate an error — "none", "rate_limit", "server_error", "timeout",
               "invalid_key", "context_length", "content_filter"
        delay_ms: Artificial delay before responding (0-5000ms)
        seed: Integer seed for deterministic responses
    """
    body = {"model": model, "messages": messages}
    extra = _mock_headers(length, response_type, error, delay_ms, seed)
    result = await _post("/v1/chat/completions", body, extra)
    return json.dumps(result, indent=2)


@mcp.tool()
async def mock_anthropic_message(
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    length: str = "medium",
    response_type: str = "auto",
    error: str = "none",
    delay_ms: int = 0,
    seed: Optional[int] = None,
) -> str:
    """
    Mock an Anthropic messages response (POST /v1/messages).
    Returns a response in exactly the Anthropic API format — drop-in compatible.

    Use this to test code that calls `anthropic.messages.create(...)` without
    spending real tokens or needing an Anthropic API key.

    Args:
        prompt: User message text
        model: Model name to appear in response (default: "claude-3-5-sonnet-20241022")
        length: Response length — "short", "medium", "long", "xl", "random"
        response_type: "auto", "text", "code", "json", "markdown", "list"
        error: Simulate — "none", "rate_limit", "server_error", "invalid_key",
               "context_length", "content_filter"
        delay_ms: Artificial delay (0-5000ms)
        seed: Integer seed for deterministic responses
    """
    body = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    extra = _mock_headers(length, response_type, error, delay_ms, seed)
    result = await _post("/anthropic/v1/messages", body, extra)
    return json.dumps(result, indent=2)


@mcp.tool()
async def mock_google_generate(
    prompt: str,
    model: str = "gemini-1.5-flash",
    length: str = "medium",
    response_type: str = "auto",
    error: str = "none",
    delay_ms: int = 0,
    seed: Optional[int] = None,
) -> str:
    """
    Mock a Google Gemini generateContent response.
    Returns a response in the Google AI Studio / Gemini API format.

    Use this to test code that calls `genai.GenerativeModel.generate_content(...)`
    without spending real tokens.

    Args:
        prompt: User message text
        model: Gemini model name (default: "gemini-1.5-flash")
        length: Response length — "short", "medium", "long", "xl", "random"
        response_type: "auto", "text", "code", "json", "markdown", "list"
        error: Simulate — "none", "rate_limit", "server_error", "invalid_key",
               "context_length", "content_filter"
        delay_ms: Artificial delay (0-5000ms)
        seed: Integer seed for deterministic responses
    """
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
    }
    extra = _mock_headers(length, response_type, error, delay_ms, seed)
    result = await _post(f"/google/v1beta/models/{model}:generateContent", body, extra)
    return json.dumps(result, indent=2)


@mcp.tool()
async def mock_simulate_error(
    provider: str = "openai",
    error_type: str = "rate_limit",
    prompt: str = "test",
) -> str:
    """
    Simulate a specific LLM API error for testing error handling code.

    Use this to verify that your retry logic, fallback handling, and error messages
    work correctly before going to production.

    Supported error types:
      - rate_limit: 429 rate limit exceeded
      - server_error: 500 internal server error
      - timeout: Request timeout simulation
      - invalid_key: 401 invalid API key
      - context_length: 400 context length exceeded
      - content_filter: 400 content policy violation

    Args:
        provider: Which provider format to use — "openai" (default), "anthropic", "google"
        error_type: The error to simulate (see above)
        prompt: Prompt text (unused in error responses, but passed through)
    """
    if provider == "anthropic":
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        extra = _mock_headers("medium", "auto", error_type, 0, None)
        try:
            result = await _post("/anthropic/v1/messages", body, extra)
            return json.dumps(result, indent=2)
        except httpx.HTTPStatusError as e:
            return f"HTTP {e.response.status_code}: {e.response.text}"
    elif provider == "google":
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        extra = _mock_headers("medium", "auto", error_type, 0, None)
        try:
            result = await _post("/google/v1beta/models/gemini-1.5-flash:generateContent", body, extra)
            return json.dumps(result, indent=2)
        except httpx.HTTPStatusError as e:
            return f"HTTP {e.response.status_code}: {e.response.text}"
    else:
        body = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]}
        extra = _mock_headers("medium", "auto", error_type, 0, None)
        try:
            result = await _post("/v1/chat/completions", body, extra)
            return json.dumps(result, indent=2)
        except httpx.HTTPStatusError as e:
            return f"HTTP {e.response.status_code}: {e.response.text}"


@mcp.tool()
async def list_mock_models(provider: str = "openai") -> str:
    """
    List available mock models for a provider.

    Args:
        provider: "openai" (default), "google"
    """
    if provider == "google":
        result = await _get("/google/v1beta/models")
    else:
        result = await _get("/v1/models")
    return json.dumps(result, indent=2)


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    """Run the Mock LLM MCP server via stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
