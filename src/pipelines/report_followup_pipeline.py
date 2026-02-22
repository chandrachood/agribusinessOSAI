from typing import Any

from src.models.gemini_client import GeminiAgent, GeminiRunner


LANG_MAP = {
    "en": "English",
    "hi": "Hindi",
    "ml": "Malayalam",
}


def _format_history(history: list[dict[str, Any]] | None, max_turns: int = 8) -> str:
    if not history:
        return "No prior Q&A."

    lines: list[str] = []
    for item in history[-max_turns:]:
        role = str(item.get("role", "user")).strip().upper()
        content = str(item.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "No prior Q&A."


async def run_report_followup(
    report_markdown: str,
    question: str,
    language: str = "en",
    history: list[dict[str, Any]] | None = None,
    session_service=None,
) -> str:
    target_lang = LANG_MAP.get(language, "English")
    history_text = _format_history(history)

    instruction = """
You are AgriBusiness OS Follow-up Assistant.
You answer user questions about a previously generated agri-business report.

Rules:
1. Use only the report content and the provided Q&A context.
2. Do not invent facts, numbers, locations, prices, or dates.
3. If details are missing in the report, clearly say the report does not contain that detail.
4. Keep the response practical and concise.
5. Use bullet points where useful.
"""

    agent = GeminiAgent(name="report_followup", instruction=instruction)
    runner = GeminiRunner(agent, "agri_os_followup", session_service)

    prompt = f"""
Target language: {target_lang}

Final report:
{report_markdown}

Previous Q&A:
{history_text}

User question:
{question}

Important:
- Respond strictly in {target_lang}.
- Ground your answer in the report content above.
"""

    answer = ""
    async for event in runner.run_async("user", "report_followup_session", prompt):
        if event.is_final_response():
            answer = (event.text or "").strip()

    if not answer:
        raise ValueError("Follow-up model returned an empty answer.")

    return answer
