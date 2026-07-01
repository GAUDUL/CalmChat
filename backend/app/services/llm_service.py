from typing import List
import logging

from app.config import settings


logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.provider = settings.llm_provider

    def generate_response(
        self,
        user_text: str,
        context: List[str],
        system_prompt: str = None,
        timeout_seconds: float | None = None,
    ) -> str:
        system_prompt = system_prompt or self.default_system_prompt()
        context_block = "\n".join(context) if context else ""

        try:
            if self.provider == "anthropic":
                return self._call_anthropic(system_prompt, context_block, user_text, timeout_seconds)
            if self.provider == "openai":
                return self._call_openai(system_prompt, context_block, user_text, timeout_seconds)
            if self.provider == "gemini":
                return self._call_gemini(system_prompt, context_block, user_text, timeout_seconds)
            return self._call_local(system_prompt, context_block, user_text, timeout_seconds)
        except Exception as exc:
            logger.exception("llm_provider_error provider=%s error=%s", self.provider, exc)
            return "I'm sorry, but the AI service is currently unavailable. Please try again later."

    def confirm_danger_signal(self, user_text: str, matched_keywords: list[str]) -> bool | None:
        prompt = (
            "Classify whether this elderly user's message indicates an immediate health "
            "or self-harm danger that should trigger emergency-level intervention. "
            "Answer with only YES or NO.\n\n"
            f"Matched keywords: {', '.join(matched_keywords)}\n"
            f"Message: {user_text}"
        )
        try:
            response = self.generate_response(
                user_text=prompt,
                context=[],
                system_prompt=(
                    "You are a strict safety triage classifier. "
                    "Return only YES for immediate danger, otherwise NO."
                ),
                timeout_seconds=settings.danger_confirmation_timeout_seconds,
            )
        except Exception as exc:
            print(f"[Danger Confirmation Error] {exc}")
            return None

        normalized = response.strip().lower()
        if normalized.startswith("yes"):
            return True
        if normalized.startswith("no"):
            return False
        return None

    def default_system_prompt(self) -> str:
        return (
            "You are a friendly AI companion who offers emotional support to elderly users. "
            "The user may speak Korean or a Korean dialect, but you must always respond in English. "
            "Use simple, short, gentle sentences that are easy to understand. "
            "Before giving advice, notice the user's feelings and acknowledge them warmly. "
            "Sound like a caring companion, not a formal assistant. "
            "If the user seems lonely, worried, tired, or sad, respond with empathy first. "
            "Ask at most one small follow-up question when it would help the user keep talking."
        )

    def _call_anthropic(self, system_prompt, context_block, user_text, timeout_seconds: float | None = None) -> str:
        import anthropic

        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=timeout_seconds,
        )
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=500,
            system=f"{system_prompt}\n\n[User profile context]\n{context_block}",
            messages=[{"role": "user", "content": user_text}],
        )
        return message.content[0].text

    def _call_openai(self, system_prompt, context_block, user_text, timeout_seconds: float | None = None) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=timeout_seconds,
        )
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": f"{system_prompt}\n\n[User profile context]\n{context_block}"},
                {"role": "user", "content": user_text},
            ],
        )
        return completion.choices[0].message.content

    def _call_gemini(self, system_prompt, context_block, user_text, timeout_seconds: float | None = None) -> str:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = (
            f"{system_prompt}\n\n"
            f"[User profile context]\n{context_block}\n\n"
            f"User:\n{user_text}"
        )
        kwargs = {}
        if timeout_seconds is not None:
            kwargs["request_options"] = {"timeout": int(timeout_seconds * 1000)}
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            **kwargs,
        )
        return response.text

    def _call_local(self, system_prompt, context_block, user_text, timeout_seconds: float | None = None) -> str:
        raise NotImplementedError("Local model provider is not implemented.")


llm_service = LLMService()
