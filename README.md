# mock-llm-mcp

MCP server for [Mock LLM API](https://mock-llm-api.rebaselabs.online) — mock OpenAI, Anthropic, and Google Gemini responses for testing AI integrations. No real API keys or token spend required.

## Installation

```bash
pip install mock-llm-mcp
# or
uvx mock-llm-mcp
```

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "mock-llm": {
      "command": "uvx",
      "args": ["mock-llm-mcp"],
      "env": {
        "MOCK_LLM_API_KEY": "your-key-here"
      }
    }
  }
}
```

> **No API key required** for the free tier (500 calls/day). Get a key at [rebaselabs.online](https://rebaselabs.online) for higher limits.

## Tools

| Tool | Description |
|------|-------------|
| `mock_quick` | Quickest mock response — provider-agnostic, auto-detects response type |
| `mock_openai_chat` | Drop-in mock for `POST /v1/chat/completions` (OpenAI format) |
| `mock_anthropic_message` | Drop-in mock for `POST /v1/messages` (Anthropic format) |
| `mock_google_generate` | Drop-in mock for Google Gemini `generateContent` |
| `mock_simulate_error` | Simulate specific LLM errors (rate limit, timeout, invalid key, etc.) |
| `list_mock_models` | List available mock models for a provider |

## Use Cases

- **Test without token spend** — verify your LLM integration code works without calling real APIs
- **CI/CD pipelines** — deterministic, offline-safe tests using seed-based responses
- **Error handling** — simulate rate limits, 500 errors, auth failures, context length exceeded
- **Frontend dev** — build chat UIs without a real API key
- **Multi-provider testing** — test your abstraction layer against OpenAI, Anthropic, and Google formats

## Examples

### Quick mock (no format needed)
```
mock_quick(prompt="Explain quantum computing", length="short")
```

### Test OpenAI integration
```
mock_openai_chat(
    messages=[{"role": "user", "content": "Hello!"}],
    model="gpt-4o",
    response_type="text"
)
```

### Simulate a rate limit error
```
mock_simulate_error(provider="anthropic", error_type="rate_limit")
```

### Deterministic response with seed
```
mock_quick(prompt="Write a haiku", seed=42)
```

## Response Control Headers

All mock tools support:
- `length`: `"short"`, `"medium"`, `"long"`, `"xl"`, `"random"`
- `response_type`: `"auto"`, `"text"`, `"code"`, `"json"`, `"markdown"`, `"list"`
- `error`: `"none"`, `"rate_limit"`, `"server_error"`, `"timeout"`, `"invalid_key"`, `"context_length"`, `"content_filter"`
- `delay_ms`: `0`–`5000` — artificial latency
- `seed`: integer — reproducible responses

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MOCK_LLM_API_KEY` | API key for authenticated access | `` (free tier) |
| `MOCK_LLM_API_URL` | Override API base URL | `https://mock-llm-api.rebaselabs.online` |

## Part of the RebaseKit Agent Infrastructure Stack

Mock LLM MCP is part of the [RebaseKit](https://rebaselabs.online) suite of agent-native APIs:

- **WeTask** — web extraction & browser automation
- **CodeExec** — sandboxed code execution
- **PII API** — detect & mask sensitive data
- **DocParse** — document parsing & OCR
- **DataTransform** — data format conversion & querying
- **Mock LLM** — mock any LLM provider for testing

> "The internet was built for humans. RebaseKit makes it work for agents."
