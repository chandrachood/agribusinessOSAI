import json
import os
from datetime import date
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from ..core.config import settings
from ..models.product import Product
from ..models.report import AnalysisReport
from ..services.source_ranking import get_ranked_sources


def run_banking_pipeline(
    product: Product, start_date: date, end_date: date
) -> AnalysisReport:
    sources = get_ranked_sources()
    raw_sources = {source.type: 0 for source in sources}

    response = _run_gemini_analysis(product, start_date, end_date, sources)
    payload = _parse_gemini_json(response)

    report_data: dict[str, Any] = {
        "product": product.name,
        "market_summary": payload["market_summary"],
        "swot": payload["swot"],
        "pestel": payload["pestel"],
        "competitors": payload["competitors"],
        "raw_sources": raw_sources,
    }
    return _validate_report(report_data)


def _run_gemini_analysis(product: Product, start_date: date, end_date: date, sources) -> str:
    api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Missing Gemini API key. Set GEMINI_API_KEY or GOOGLE_API_KEY.")

    model_id = settings.gemini_model_id or os.environ.get("GEMINI_MODEL_ID") or "gemini-flash-lite-latest"
    source_names = ", ".join([s.name for s in sources])
    prompt = f"""
You are a market analyst. Produce an evidence-oriented analysis for this product.

Product Name: {product.name}
Product URL: {product.url or "Not provided"}
Region: {product.country}
Segment: {product.segment or "Not provided"}
Date Window: {start_date.isoformat()} to {end_date.isoformat()}
Candidate Source Platforms: {source_names}

Return STRICT JSON only, with no markdown, no explanation, and no code fences.
Do not use placeholders or dummy values like "TBD", "N/A", "stub", "dummy", "example", or "lorem ipsum".
If a specific fact is uncertain, say that clearly in natural language inside the relevant field.
JSON schema:
{{
  "market_summary": "string",
  "swot": {{
    "strengths": ["string"],
    "weaknesses": ["string"],
    "opportunities": ["string"],
    "threats": ["string"]
  }},
  "pestel": {{
    "political": ["string"],
    "economic": ["string"],
    "social": ["string"],
    "technological": ["string"],
    "environmental": ["string"],
    "legal": ["string"]
  }},
  "competitors": [
    {{
      "name": "string",
      "summary": "string",
      "pros": ["string"],
      "cons": ["string"]
    }}
  ]
}}
"""

    client = genai.Client(api_key=api_key)
    result = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )

    text = (result.text or "").strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")
    return text


def _parse_gemini_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or start >= end:
            raise ValueError("Gemini response was not valid JSON.")
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini response could not be parsed as JSON.") from exc

    required_keys = {"market_summary", "swot", "pestel", "competitors"}
    missing = required_keys - set(parsed.keys())
    if missing:
        raise ValueError(f"Gemini JSON missing required keys: {', '.join(sorted(missing))}")
    return parsed


def _validate_report(report_data: dict[str, Any]) -> AnalysisReport:
    try:
        if hasattr(AnalysisReport, "model_validate"):
            return AnalysisReport.model_validate(report_data)
        return AnalysisReport.parse_obj(report_data)
    except ValidationError as exc:
        raise ValueError(f"Gemini output failed schema validation: {exc}") from exc
