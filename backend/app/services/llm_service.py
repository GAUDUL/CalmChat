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
            "Acknowledge the user's feelings warmly. "
            "When appropriate, refer to the user's message and ask one gentle, open-ended question to keep the conversation going. "
            "Avoid repetitive phrases and avoid unnecessary questions in urgent situations."
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
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = (
            f"{system_prompt}\n\n"
            f"[User profile context]\n{context_block}\n\n"
            f"User:\n{user_text}"
        )
        config = None
        if timeout_seconds is not None:
            config = types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000))
            )
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config,
        )
        return response.text

    def _call_local(self, system_prompt, context_block, user_text, timeout_seconds: float | None = None) -> str:
        raise NotImplementedError("Local model provider is not implemented.")
    
    def correct_transcript(self, text: str) -> str:
        try:
            corrected = self.generate_response(
                user_text=f"Transcript:\n{text}",
                context=[],
                system_prompt=(
                    "You correct speech-to-text transcription errors. "
                    "Fix only obvious recognition mistakes. "
                    "Do not add information or change the meaning. "
                    "If unsure, return the original text exactly. "
                    "Return only the corrected transcript."
                ),
            ).strip()

            return corrected or text

        except Exception:
            return text



    def confirm_guilt_or_regret_signal(self, user_text: str) -> bool | None:
        """
        [lift 분석 근거] KOTE의 '죄책감' 라벨은 base-rate 대비 lift < 1로 신뢰 불가.
        자기지향_부정 클러스터가 top-2 후보로 뜬 경우에만 이 함수로 보조 확인한다.
        """
        prompt = (
            "Classify whether this elderly Korean user's message expresses guilt "
            "or regret (self-blame about something they did or failed to do), "
            "as opposed to shame, inferiority, or general sadness. "
            "Answer with only YES or NO.\n\n"
            f"Message: {user_text}"
        )
        try:
            response = self.generate_response(
                user_text=prompt,
                context=[],
                system_prompt=(
                    "You are a strict emotion classifier specialized in distinguishing "
                    "guilt/regret from other negative self-directed emotions. "
                    "Return only YES or NO."
                ),
                timeout_seconds=settings.danger_confirmation_timeout_seconds,
            )
        except Exception as exc:
            print(f"[Guilt/Regret Confirmation Error] {exc}")
            return None

        normalized = response.strip().lower()
        if normalized.startswith("yes"):
            return True
        if normalized.startswith("no"):
            return False
        return None

llm_service = LLMService()
