# backend/test_llm.py
from app.services.llm_service import llm_service

if __name__ == "__main__":
    print("provider:", llm_service.provider)

    response = llm_service.generate_response("안녕하세요, 오늘 기분이 어때요?", context=[])
    print("일반 응답:", response)

    guilt_result = llm_service.confirm_guilt_or_regret_signal(
        "내가 잘못해서 미안하고 계속 후회돼요"
    )
    print("죄책감/후회 판단 결과:", guilt_result)