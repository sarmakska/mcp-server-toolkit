"""SarmaLink-AI plugin: expose chat, summarise, classify as MCP tools."""
import os

import httpx

from ...registry import registry

BASE_URL = os.getenv("MCP_SARMALINK_BASE_URL", "https://api.sarmalink.ai/v1")
API_KEY = os.getenv("MCP_SARMALINK_API_KEY", "")


async def _chat(prompt: str, system: str = "") -> str:
    if not API_KEY:
        return "(SarmaLink API key not configured. Set MCP_SARMALINK_API_KEY.)"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "smart",
        "messages": (
            [{"role": "system", "content": system}] if system else []
        ) + [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{BASE_URL}/chat/completions", headers=headers, json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


@registry.tool("ai_chat", description="Send a prompt to SarmaLink-AI and get the answer")
async def ai_chat(prompt: str) -> str:
    return await _chat(prompt)


@registry.tool("summarise", description="Summarise text via SarmaLink-AI")
async def summarise(text: str) -> str:
    return await _chat(text, system="Summarise the following text in three crisp bullet points.")


@registry.tool("classify", description="Classify text into one of the provided labels")
async def classify(text: str, labels: str) -> str:
    return await _chat(
        f"Text: {text}\nLabels: {labels}",
        system="Pick the single best matching label. Return only the label.",
    )
