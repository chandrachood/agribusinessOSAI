import asyncio
import re
from typing import Any, Callable, Dict

from google.genai import types

from src.agents.definitions import build_agents
from src.models.gemini_client import GeminiRunner


def _build_citation_index(
    per_agent_sources: dict[str, list[dict[str, str]]]
) -> list[dict[str, str | int]]:
    order = [
        ("location_check", "Location Check"),
        ("weather_analysis", "Weather Analysis"),
        ("market_timing", "Market Timing"),
        ("sales_channels", "Sales Channels"),
        ("storage_proximity", "Storage Proximity"),
    ]

    seen_urls: set[str] = set()
    citation_index: list[dict[str, str | int]] = []
    next_id = 1

    for key, label in order:
        for src in per_agent_sources.get(key) or []:
            url = (src.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            citation_index.append(
                {
                    "id": next_id,
                    "title": (src.get("title") or url).strip(),
                    "url": url,
                    "agent": label,
                }
            )
            next_id += 1

    return citation_index


def _format_citation_catalog(citation_index: list[dict[str, str | int]]) -> str:
    if not citation_index:
        return "No citations available."

    lines = ["Citation catalog (use these marker IDs exactly):"]
    for item in citation_index:
        lines.append(f"[{item['id']}] {item['title']} ({item['agent']}) - {item['url']}")
    return "\n".join(lines)


def _format_source_block(citation_index: list[dict[str, str | int]]) -> str:
    if not citation_index:
        return ""

    lines = ["", "## Validation Sources"]
    for item in citation_index:
        lines.append(f"- [{item['id']}] [{item['title']}]({item['url']}) ({item['agent']})")
    return "\n".join(lines)


def _has_inline_citation_markers(text: str) -> bool:
    return bool(re.search(r"\[\d+\]", text or ""))


async def run_agribusiness_pipeline(
    user_input: str,
    progress_cb: Callable[[Dict[str, Any]], None],
    session_service=None,
    language: str = "en",
):
    """
    Orchestrates the expert-agent pipeline:
    1) Cultivator
    2) Location Check (search-grounded)
    3) Crop-for-Soil
    4) Weather Analysis (search-grounded)
    5) Market Timing (search-grounded)
    6) Sales Channels (search-grounded)
    7) Storage Proximity (search-grounded)
    8) Perishability Risk
    9) Final Consolidator
    """

    agents = build_agents()

    lang_map = {
        "en": "English",
        "hi": "Hindi",
        "ml": "Malayalam",
    }
    target_lang = lang_map.get(language, "English")

    def search_tools() -> list[types.Tool]:
        return [types.Tool(google_search=types.GoogleSearch())]

    async def run_agent(
        agent_key: str,
        content: str,
        use_google_search: bool = False,
    ) -> tuple[str, list[dict[str, str]]]:
        runner = GeminiRunner(agents[agent_key], "agri_os", session_service)
        result_text = ""
        result_sources: list[dict[str, str]] = []
        progress_cb({"step": agent_key, "status": "running"})

        lang_instruction = (
            f"\n\nIMPORTANT: You must output your response strictly in {target_lang} language."
        )
        final_content = content + lang_instruction

        if use_google_search:
            result_text, result_sources = await runner.run_once(
                "user",
                "session",
                final_content,
                tools=search_tools(),
                temperature=0.2,
            )
        else:
            async for event in runner.run_async(
                "user",
                "session",
                final_content,
                tools=None,
                temperature=0.2,
            ):
                if event.is_final_response():
                    result_text = event.text

        progress_cb({"step": agent_key, "status": "completed", "output": result_text})
        return result_text, result_sources

    progress_cb(
        {
            "step": "pipeline_start",
            "status": "running",
            "message": f"Starting AgriBusiness OS Analysis in {target_lang}...",
        }
    )

    per_agent_sources: dict[str, list[dict[str, str]]] = {}

    cultivator_profile, _ = await run_agent("cultivator", f"Farmer Input:\n{user_input}")

    location_soil_report, location_sources = await run_agent(
        "location_check",
        f"""
Farmer Input:
{user_input}

Cultivator Profile:
{cultivator_profile}
""",
        use_google_search=True,
    )
    per_agent_sources["location_check"] = location_sources

    crop_recommendations, _ = await run_agent(
        "crop_for_soil",
        f"""
Farmer Input:
{user_input}

Cultivator Profile:
{cultivator_profile}

Location and Soil Validation:
{location_soil_report}
""",
    )

    shared_context = f"""
Farmer Input:
{user_input}

Cultivator Profile:
{cultivator_profile}

Location and Soil Validation:
{location_soil_report}

Crop Recommendations:
{crop_recommendations}
"""

    parallel_results = await asyncio.gather(
        run_agent("weather_analysis", shared_context, use_google_search=True),
        run_agent("market_timing", shared_context, use_google_search=True),
        run_agent("sales_channels", shared_context, use_google_search=True),
        run_agent("storage_proximity", shared_context, use_google_search=True),
    )
    (weather_report, weather_sources), (market_report, market_sources), (
        sales_report,
        sales_sources,
    ), (
        storage_report,
        storage_sources,
    ) = parallel_results
    per_agent_sources["weather_analysis"] = weather_sources
    per_agent_sources["market_timing"] = market_sources
    per_agent_sources["sales_channels"] = sales_sources
    per_agent_sources["storage_proximity"] = storage_sources

    perishability_report, _ = await run_agent(
        "perishability_risk",
        f"""
{shared_context}

Weather Report:
{weather_report}

Market Timing Report:
{market_report}

Sales Channels Report:
{sales_report}

Storage Proximity Report:
{storage_report}
""",
    )

    citation_index = _build_citation_index(per_agent_sources)
    citation_catalog = _format_citation_catalog(citation_index)

    final_plan, _ = await run_agent(
        "final_consolidator",
        f"""
Please consolidate all reports into one actionable final recommendation.

Farmer Input:
{user_input}

Cultivator Profile:
{cultivator_profile}

Location and Soil Validation:
{location_soil_report}

Crop Recommendations:
{crop_recommendations}

Weather Report:
{weather_report}

Market Timing Report:
{market_report}

Sales Channels Report:
{sales_report}

Storage Proximity Report:
{storage_report}

Perishability and Risk Report:
{perishability_report}

Inline citation requirement:
- Use inline citation markers like [1], [2] for factual claims in sections 2-7.
- Use only IDs from the citation catalog below.
- Do not invent citation IDs.

{citation_catalog}
""",
    )

    final_body = (final_plan or "").strip()
    if citation_index and not _has_inline_citation_markers(final_body):
        marker_str = " ".join([f"[{item['id']}]" for item in citation_index[:3]])
        final_body += (
            "\n\n> Evidence markers were auto-added for validation: "
            f"{marker_str}. Refer to the Validation Sources section below."
        )

    final_with_sources = final_body + _format_source_block(citation_index)
    progress_cb({"step": "pipeline_complete", "status": "completed", "output": final_with_sources})
    return final_with_sources
