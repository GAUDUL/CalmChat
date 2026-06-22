"""
LLM 추상화 레이어.
팀에서 Claude / GPT-4o / Gemini / 로컬 모델 중 무엇을 쓸지 결정되지 않았으므로,
.env의 LLM_PROVIDER 값만 바꾸면 router/service 코드를 건드리지 않고 교체 가능하도록 구성.
"""
from typing import List
from app.config import settings


class LLMService:
    def __init__(self):
        self.provider = settings.llm_provider

    def generate_response(self, user_text: str, context: List[str], system_prompt: str = None) -> str:
        system_prompt = system_prompt or self._default_system_prompt()
        context_block = "\n".join(context) if context else ""

        if self.provider == "anthropic":
            return self._call_anthropic(system_prompt, context_block, user_text)
        elif self.provider == "openai":
            return self._call_openai(system_prompt, context_block, user_text)
        elif self.provider == "gemini":
            return self._call_gemini(system_prompt, context_block, user_text)
        else:
            return self._call_local(system_prompt, context_block, user_text)

    def _default_system_prompt(self) -> str:
        return (
            "당신은 노인 사용자의 정서적 동반자 역할을 하는 친근한 AI입니다. "
            "쉽고 짧은 문장을 사용하고, 사용자의 감정을 먼저 살피며 따뜻하게 응답하세요."
        )

    def _call_anthropic(self, system_prompt, context_block, user_text) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=500,
            system=f"{system_prompt}\n\n[사용자 프로파일 컨텍스트]\n{context_block}",
            messages=[{"role": "user", "content": user_text}],
        )
        return message.content[0].text

    def _call_openai(self, system_prompt, context_block, user_text) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": f"{system_prompt}\n\n[사용자 프로파일 컨텍스트]\n{context_block}"},
                {"role": "user", "content": user_text},
            ],
        )
        return completion.choices[0].message.content

    # 현재는 gemini 사용
    def _call_gemini(self, system_prompt, context_block, user_text) -> str:
        from google import genai

        client = genai.Client(
            api_key=settings.gemini_api_key
        )
        prompt = f"""

    {system_prompt}

    [사용자 프로파일 컨텍스트]
    {context_block}

    사용자:
    {user_text}
    """

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt
        )

        return response.text

    def _call_local(self, system_prompt, context_block, user_text) -> str:
        # TODO: 로컬 모델(llama.cpp, vLLM 등) 연동
        raise NotImplementedError("로컬 모델 provider 미구현")


llm_service = LLMService()
