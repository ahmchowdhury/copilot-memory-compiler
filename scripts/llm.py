"""LLM abstraction layer — supports Azure OpenAI and OpenAI."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_client():
    """Return an OpenAI-compatible client based on environment config."""
    from openai import AzureOpenAI, OpenAI

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if endpoint:
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        if api_key:
            return AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            )
        # Key auth disabled — use Entra ID (Azure AD) token auth
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        return AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        )
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def get_model() -> str:
    """Return the model/deployment name to use."""
    return os.environ.get("LLM_MODEL", os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"))


def chat(messages: list[dict], json_mode: bool = False, max_tokens: int = 16000) -> str:
    """Send a chat completion and return the response text."""
    client = get_client()
    kwargs = {
        "model": get_model(),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""
