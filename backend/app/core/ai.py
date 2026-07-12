import httpx

from app.core.config import settings

TONE_INSTRUCTIONS = {
    "friendly": "warm, casual, and friendly",
    "formal": "polite, professional, and formal",
    "promotional": "upbeat and promotional, encouraging the customer to book again",
}


class AIDraftError(Exception):
    pass


async def draft_reminder_message(
    business_name: str,
    appointment_title: str,
    contact_name: str,
    tone: str | None,
    custom_prompt: str | None,
) -> str:
    if custom_prompt:
        instruction = custom_prompt
    else:
        style = TONE_INSTRUCTIONS.get(tone or "friendly", TONE_INSTRUCTIONS["friendly"])
        instruction = f"Write a {style} appointment reminder message."

    prompt = (
        f"{instruction}\n\n"
        f"Context: {business_name} is reminding {contact_name} about their upcoming "
        f'"{appointment_title}" appointment.\n'
        "Keep it under 40 words, no subject line, no placeholders, just the message body."
    )

    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
    except httpx.HTTPError as exc:
        raise AIDraftError(f"Could not reach Ollama: {exc}") from exc

    if response.status_code >= 400:
        raise AIDraftError(f"Ollama returned {response.status_code}: {response.text}")

    return response.json()["response"].strip()
