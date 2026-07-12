"""
Lightweight Mistral chat client for low-cost cognitive tasks (dream, curiosity).
Uses MISTRAL_API_KEY from environment.
"""
from __future__ import annotations

import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DREAM_MODEL = os.getenv("MISTRAL_DREAM_MODEL", "mistral-small-latest")
DEFAULT_CURIOSITY_MODEL = os.getenv("MISTRAL_CURIOSITY_MODEL", DEFAULT_DREAM_MODEL)
API_URL = "https://api.mistral.ai/v1/chat/completions"


def mistral_available() -> bool:
    return bool(os.getenv("MISTRAL_API_KEY", "").strip())


def mistral_chat(
    prompt: str,
    *,
    system: str = "",
    model: Optional[str] = None,
    max_tokens: int = 900,
    temperature: float = 0.35,
) -> str:
    """Blocking chat completion. Returns empty string on failure."""
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if not api_key or not (prompt or "").strip():
        return ""

    messages = []
    if system.strip():
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": prompt.strip()})

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model or DEFAULT_DREAM_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return str(message.get("content", "") or "").strip()
    except Exception as exc:
        print(f"[MistralClient] Request failed: {exc}")
        return ""


async def mistral_chat_async(
    prompt: str,
    *,
    system: str = "",
    model: Optional[str] = None,
    max_tokens: int = 900,
    temperature: float = 0.35,
) -> str:
    import asyncio
    return await asyncio.to_thread(
        mistral_chat,
        prompt,
        system=system,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
