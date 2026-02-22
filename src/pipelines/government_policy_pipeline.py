import logging
import os
from typing import Any
from urllib.parse import urlparse
import re

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

LANG_MAP = {
    "en": "English",
    "hi": "Hindi",
    "ml": "Malayalam",
}


def _extract_text(response: Any) -> str:
    text = (getattr(response, "text", "") or "").strip()
    if text:
        return text

    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            chunk = (getattr(part, "text", "") or "").strip()
            if chunk:
                return chunk
    return ""


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        clean += f"?{parsed.query}"
    return clean


def _extract_sources(response: Any) -> list[dict[str, str]]:
    seen: set[str] = set()
    sources: list[dict[str, str]] = []

    for candidate in getattr(response, "candidates", []) or []:
        grounding = getattr(candidate, "grounding_metadata", None)
        chunks = getattr(grounding, "grounding_chunks", None) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if not web:
                continue

            uri = _normalize_url(getattr(web, "uri", "") or "")
            if not uri or uri in seen:
                continue

            seen.add(uri)
            sources.append(
                {
                    "title": (getattr(web, "title", "") or "").strip() or uri,
                    "url": uri,
                    "domain": (getattr(web, "domain", "") or "").strip(),
                }
            )

    return sources


def _extract_urls_from_text(text: str) -> list[str]:
    return [m.group(0) for m in re.finditer(r"https?://[^\s)]+", text or "")]


def _build_prompt(location: str, crops: str, target_lang: str) -> str:
    return f"""
Farmer context:
- Location: {location}
- Crops grown/planned: {crops}

Task:
Search and compile currently active or recently valid Indian government schemes relevant to this farmer.
Focus on both central and state schemes for the provided location.

Return a structured markdown report with these exact sections:
1. Subsidies
2. Loans and Credit
3. Insurance and Risk Cover
4. Other Government Offers and Incentives

For each scheme include:
- Scheme name
- Scheme level: Central or State
- Relevant crop/location fit
- Benefit summary
- Eligibility snapshot
- How to avail: step-by-step process
- Documents usually required
- Where to apply (portal/office)
- Deadline/timeliness note (if available)
- At least one official source URL

Rules:
- Include only verifiable schemes backed by web sources.
- Prefer official government sources (.gov.in, state portals, ministry, PMFBY, NABARD, etc.).
- If a category has no verified scheme, explicitly say "No verified schemes found for this category."
- Do not use markdown tables. Use bullet points/subheadings for each scheme.
- Do not invent policy names, dates, amounts, or eligibility rules.
- Keep guidance practical for a farmer to apply.
- Respond strictly in {target_lang}.
"""


async def run_government_policy_search(
    location: str,
    crops: str,
    language: str = "en",
) -> dict[str, Any]:
    location = (location or "").strip()
    crops = (crops or "").strip()
    if not location:
        raise ValueError("Location is required.")
    if not crops:
        raise ValueError("Crops are required.")

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key is missing. Set GEMINI_API_KEY or GOOGLE_API_KEY.")

    configured_model = (
        os.environ.get("GEMINI_MODEL_ID")
        or os.environ.get("GOOGLE_GEMINI_MODEL")
        or "gemini-flash-lite-latest"
    )
    model_candidates = [configured_model]
    if configured_model != "gemini-2.0-flash":
        model_candidates.append("gemini-2.0-flash")

    target_lang = LANG_MAP.get(language, "English")
    prompt = _build_prompt(location, crops, target_lang)

    client = genai.Client(api_key=api_key)

    try:
        config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=(
                "You are an Indian agri-policy advisor. Use web search grounding and provide only verified guidance."
            ),
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )

        last_error = None
        for model_id in model_candidates:
            try:
                response = await client.aio.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=config,
                )
                report = _extract_text(response).strip()
                if not report:
                    raise ValueError("Policy search returned an empty response.")

                sources = _extract_sources(response)
                if not sources:
                    seen: set[str] = set()
                    for url in _extract_urls_from_text(report):
                        clean = _normalize_url(url)
                        if clean and clean not in seen:
                            seen.add(clean)
                            sources.append({"title": clean, "url": clean, "domain": ""})

                return {
                    "report_markdown": report,
                    "sources": sources,
                }
            except Exception as exc:
                logger.warning(
                    "Policy search failed on model %s, trying fallback if available: %s",
                    model_id,
                    exc,
                )
                last_error = exc

        if last_error:
            raise last_error
        raise ValueError("Policy search failed before generating a response.")
    except Exception as exc:
        logger.exception("Government policy search failed: %s", exc)
        raise
    finally:
        try:
            if hasattr(client, "aio") and hasattr(client.aio, "aclose"):
                await client.aio.aclose()
        except Exception as exc:
            logger.debug("Gemini aio close failed: %s", exc)

        try:
            if hasattr(client, "close"):
                client.close()
        except Exception as exc:
            logger.debug("Gemini close failed: %s", exc)
