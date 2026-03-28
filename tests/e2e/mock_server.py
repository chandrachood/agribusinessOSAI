import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


async def fake_agribusiness_pipeline(user_input, progress_cb, session_service=None, language="en"):
    progress_cb(
        {
            "step": "pipeline_start",
            "status": "running",
            "message": f"Starting AgriBusiness OS AI Analysis in {language}",
        }
    )
    await asyncio.sleep(0.05)

    progress_cb({"step": "cultivator", "status": "running"})
    await asyncio.sleep(0.05)
    progress_cb(
        {
            "step": "cultivator",
            "status": "completed",
            "output": f"Parsed farmer input: {user_input}",
        }
    )
    await asyncio.sleep(0.05)

    progress_cb({"step": "final_consolidator", "status": "running"})
    await asyncio.sleep(0.05)
    final_report = f"""# Mock Decision Report

## Executive Summary
- Farmer input received: {user_input}
- Selected UI language: {language} [1]

## 30-60-90 Day Action Plan
- Week 1: Validate soil and water assumptions.
- Week 2: Shortlist crops and buyers.

## Validation Sources
- [1] [Mock Source](https://example.com/mock-source) (Mock)
"""
    progress_cb(
        {
            "step": "final_consolidator",
            "status": "completed",
            "output": final_report,
        }
    )
    return final_report


async def fake_followup_pipeline(
    report_markdown,
    question,
    language="en",
    history=None,
    session_service=None,
):
    history_len = len(history or [])
    return (
        f"## Follow-up answer\n"
        f"- Question: {question}\n"
        f"- Language: {language}\n"
        f"- History turns received: {history_len}\n"
        f"- Recommendation: Proceed with the mock action plan."
    )


async def fake_policy_pipeline(location, crops, language="en"):
    return {
        "report_markdown": (
            "## Subsidies\n"
            f"- Mock subsidy for {location} covering {crops}.\n\n"
            "## Loans and Credit\n"
            "- Mock working capital support."
        ),
        "sources": [
            {
                "title": "Mock Policy Portal",
                "url": "https://example.gov.in/mock-policy",
            }
        ],
    }


main._get_agribusiness_pipeline = lambda: fake_agribusiness_pipeline
main._get_report_followup_pipeline = lambda: fake_followup_pipeline
main._get_government_policy_pipeline = lambda: fake_policy_pipeline


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5010"))
    main.app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
