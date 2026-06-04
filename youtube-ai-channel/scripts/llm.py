"""
llm.py
Unified LLM interface supporting multiple providers.
Primary: DeepSeek (via OpenAI SDK) — $0.14/M input, $0.28/M output
Fallback: Anthropic — $3/M input, $15/M output
Also: OpenRouter — free access to DeepSeek, Gemini, Mistral, etc.

Set LLM_PROVIDER=deepseek (default), openrouter, or anthropic in .env
"""

import os
import json
from pathlib import Path

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "deepseek").lower()

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def chat(
    messages: list,
    model: str = None,
    max_tokens: int = 4096,
    system_prompt: str = None,
    temperature: float = 0.7,
) -> str:
    """Send a chat completion request and return the response text.

    Args:
        messages: List of {"role": "user"/"assistant", "content": "..."}
        model: Model name (provider-specific). If None, uses config default.
        max_tokens: Maximum tokens in response
        system_prompt: Optional system message prepended to the conversation
        temperature: Response creativity (0-1)

    Returns:
        Response text string
    """
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    if LLM_PROVIDER == "deepseek":
        return _chat_deepseek(messages, model, max_tokens, temperature)
    elif LLM_PROVIDER == "openrouter":
        return _chat_openrouter(messages, model, max_tokens, temperature)
    elif LLM_PROVIDER == "anthropic":
        return _chat_anthropic(messages, model, max_tokens, temperature)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}. Use: deepseek, openrouter, anthropic")


def _chat_deepseek(
    messages: list, model: str, max_tokens: int, temperature: float
) -> str:
    """Call DeepSeek via OpenAI-compatible API."""
    if not DEEPSEEK_API_KEY:
        raise ValueError(
            "DEEPSEEK_API_KEY required for DeepSeek. "
            "Get one at https://platform.deepseek.com/api_keys"
        )
    from openai import OpenAI

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    model = model or "deepseek-chat"

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def _chat_openrouter(
    messages: list, model: str, max_tokens: int, temperature: float
) -> str:
    """Call OpenRouter API (free access to many models)."""
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY required. "
            "Get one at https://openrouter.ai/keys"
        )
    from openai import OpenAI

    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    model = model or "deepseek/deepseek-chat"

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def _chat_anthropic(
    messages: list, model: str, max_tokens: int, temperature: float
) -> str:
    """Call Anthropic Claude API (fallback, most expensive)."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY required for Anthropic provider")
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system = None
    chat_messages = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            chat_messages.append(m)

    if not chat_messages:
        chat_messages = messages

    config_model = _get_config_model()
    model = model or config_model or "claude-sonnet-4-6"

    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        messages=chat_messages,
        temperature=temperature,
    )
    if system:
        kwargs["system"] = system

    resp = client.messages.create(**kwargs)
    return resp.content[0].text


def _get_config_model() -> str:
    """Read model from channel_config.json if it exists."""
    config_path = Path("config/channel_config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        return config.get("model")
    return None
