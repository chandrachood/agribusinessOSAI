import os
import asyncio
import logging
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

from google.adk.agents import LlmAgent
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# User requested cheapest model
DEFAULT_MODEL_ID = "gemini-flash-lite-latest"


class GeminiAgent(LlmAgent):
    """Light wrapper to keep ADK-compatible agent definition."""

    def __init__(self, *args, model: str | None = None, **kwargs):
        resolved_model = (
            model
            or os.environ.get("GEMINI_MODEL_ID")
            or os.environ.get("GOOGLE_GEMINI_MODEL")
            or DEFAULT_MODEL_ID
        )
        super().__init__(*args, model=resolved_model, **kwargs)


class GeminiEvent:
    """Mimics google.adk.runners.Runner event structure."""

    def __init__(self, text: str, is_final: bool = True):
        self.text = text
        self._is_final = is_final
        # Create a dummy content object if needed for compatibility, 
        # though consumers mostly use .text
        self.content = types.Content(parts=[types.Part(text=text)])

    def is_final_response(self) -> bool:
        return self._is_final


class GeminiRunner:
    """Executes a GeminiAgent using the Google GenAI SDK."""

    def __init__(self, agent: GeminiAgent, app_name: str, session_service=None):
        self.agent = agent
        self.app_name = app_name
        self.session_service = session_service

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY."
            )

        self.client = genai.Client(api_key=api_key)

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse((url or "").strip())
        if not parsed.scheme or not parsed.netloc:
            return ""
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            clean += f"?{parsed.query}"
        return clean

    @staticmethod
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

    def _extract_sources(self, response: Any) -> list[dict[str, str]]:
        seen: set[str] = set()
        sources: list[dict[str, str]] = []

        for candidate in getattr(response, "candidates", []) or []:
            grounding = getattr(candidate, "grounding_metadata", None)
            chunks = getattr(grounding, "grounding_chunks", None) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if not web:
                    continue

                uri = self._normalize_url(getattr(web, "uri", "") or "")
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

    async def run_once(
        self,
        user_id: str,
        session_id: str,
        new_message: types.Content,
        tools: list[types.Tool] | None = None,
        temperature: float | None = None,
    ) -> tuple[str, list[dict[str, str]]]:
        system_instruction = self.agent.instruction or ""

        user_text = ""
        if hasattr(new_message, "parts") and new_message.parts:
            user_text = new_message.parts[0].text
        elif isinstance(new_message, str):
            user_text = new_message

        config_kwargs = {
            "system_instruction": system_instruction,
        }
        if tools:
            config_kwargs["tools"] = tools
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        config = types.GenerateContentConfig(**config_kwargs)

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_text)],
            )
        ]

        try:
            response = await self.client.aio.models.generate_content(
                model=self.agent.model,
                contents=contents,
                config=config,
            )
            text = self._extract_text(response)
            sources = self._extract_sources(response)
            return text, sources
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        """Close sync + async transports to avoid pending close tasks on loop shutdown."""
        if not self.client:
            return

        # Close async transport first so BaseApiClient doesn't need to schedule cleanup later.
        try:
            if hasattr(self.client, "aio") and hasattr(self.client.aio, "aclose"):
                await self.client.aio.aclose()
        except Exception as exc:
            logger.debug(f"Gemini async close failed: {exc}")

        try:
            if hasattr(self.client, "close"):
                self.client.close()
        except Exception as exc:
            logger.debug(f"Gemini close failed: {exc}")

        self.client = None

    async def run_async(
        self,
        user_id: str,
        session_id: str,
        new_message: types.Content,
        tools: list[types.Tool] | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[GeminiEvent, None]:
        system_instruction = self.agent.instruction or ""
        
        # Extract text from the input message
        user_text = ""
        if hasattr(new_message, 'parts') and new_message.parts:
            user_text = new_message.parts[0].text
        elif isinstance(new_message, str):
            user_text = new_message

        # Config per user request
        config_kwargs = {
            "system_instruction": system_instruction,
        }
        if tools:
            config_kwargs["tools"] = tools
        if temperature is not None:
            config_kwargs["temperature"] = temperature

        config = types.GenerateContentConfig(**config_kwargs)

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_text)],
            )
        ]

        logger.info(f"Using model: {self.agent.model}")

        # Streaming generation
        try:
            # We must wrap the sync generator in an async context or run in executor if it blocks.
            # google-genai client methods are often sync, but we want async behavior.
            # For simplicity in this loop, we run in executor.
            
            loop = asyncio.get_running_loop()
            
            # Note: models.generate_content_stream is a generator. 
            # We cannot easily run a generator in run_in_executor. 
            # We will use the sync iterator but offload the *call* if possible, 
            # but standard practice with this SDK for async apps is often just iterating if it's fast enough,
            # or using the async client if available (google-genai < 1.0 might vary).
            # The user snippet used sync: client.models.generate_content_stream
            
            # To avoid blocking the event loop in a real async app, we should ideally use an async compatible method
            # or run the whole blocking chunk operation in a thread.
            # For this implementation, I will iterate synchronously but yield to the loop. 
            
            # However, looking at the reference implementation `oracle-postgres-gemini-prod`, 
            # they used `client.models.generate_content` (non-stream) in `run_in_executor`.
            # I will assume we want streaming.
            
            # Let's try to stick to a simple non-blocking approach where possible.
            # But the user specifically asked for "cheapest" and provided a snippet.
            # I will use `generate_content_stream` directly.
            
            response_stream = self.client.models.generate_content_stream(
                model=self.agent.model,
                contents=contents,
                config=config,
            )

            accumulated_text = ""
            for chunk in response_stream:
                if chunk.text:
                   chunk_txt = chunk.text
                   accumulated_text += chunk_txt
                   yield GeminiEvent(text=chunk_txt, is_final=False)
                   # Allow other tasks to run
                   await asyncio.sleep(0)
            
            # Send a final event with the FULL accumulated text
            yield GeminiEvent(text=accumulated_text, is_final=True)

        except Exception as exc:
            logger.error(f"Gemini error: {exc}")
            yield GeminiEvent(text=f"Error: {str(exc)}", is_final=True)
        finally:
            await self.aclose()
