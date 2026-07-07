"""
aihub_emotion_analysis.py

AI Hub 감성대화 말뭉치(최종데이터) 파싱 및 분포 분석
- HS01 발화 + 감정 코드(E10~E69) 추출
- 노년층(A04) 서브셋 분리
- KOTE 매핑 작업을 위한 전처리 산출물 생성
"""

import json
from pathlib import Path
from collections import Counter

import pandas as pd


# ============================================================
# 0. 코드북 정의 (가이드라인 PDF 15~16페이지 기준)
# ============================================================

AGE_CODE = {
    "A01": "청소년",
    "A02": "청년",
    "A03": "중년",
    "A04": "노년",
}

GENDER_CODE = {
    "G01": "남성",
    "G02": "여성",
}

SITUATION_CODE = {
    "S01": "가족관계", "S02": "학업및진로", "S03": "학교폭력/따돌림", "S04": "대인관계",
    "S05": "연애,결혼,출산", "S06": "진로,취업,직장", "S07": "대인관계(부부,자녀)",
    "S08": "재정,은퇴,노후준비", "S09": "건강", "S10": "직장,업무스트레스",
    "S11": "건강,죽음", "S12": "대인관계(노년)", "S13": "재정",
}

DISEASE_CODE = {
    "D01": "만성질환 유",
    "D02": "만성질환 무",
}

EMOTION_CODE = {
    "E10": "분노", "E11": "툴툴대는", "E12": "좌절한", "E13": "짜증내는", "E14": "방어적인",
    "E15": "악의적인", "E16": "안달하는", "E17": "구역질나는", "E18": "노여워하는", "E19": "성가신",
    "E20": "슬픔", "E21": "실망한", "E22": "비통한", "E23": "후회되는", "E24": "우울한",
    "E25": "마비된", "E26": "염세적인", "E27": "눈물이나는", "E28": "낙담한", "E29": "환멸을느끼는",
    "E30": "불안", "E31": "두려운", "E32": "스트레스받는", "E33": "취약한", "E34": "혼란스러운",
    "E35": "당혹스러운", "E36": "회의적인", "E37": "걱정스러운", "E38": "조심스러운", "E39": "초조한",
    "E40": "상처", "E41": "질투하는", "E42": "배신당한", "E43": "고립된", "E44": "충격받은",
    "E45": "가난한/불우한", "E46": "희생된", "E47": "억울한", "E48": "괴로워하는", "E49": "버려진",
    "E50": "당황", "E51": "고립된(당황)", "E52": "남의시선의식", "E53": "외로운", "E54": "열등감",
    "E55": "죄책감의", "E56": "부끄러운", "E57": "혐오스러운", "E58": "한심한", "E59": "혼란스러운(당황)",
    "E60": "기쁨", "E61": "감사하는", "E62": "신뢰하는", "E63": "편안한", "E64": "만족스러운",
    "E65": "흥분", "E66": "느긋", "E67": "안도", "E68": "신이난", "E69": "자신하는",
}

EMOTION_MAJOR_PREFIX_MAP = {
    "E1": "분노", "E2": "슬픔", "E3": "불안",
    "E4": "상처", "E5": "당황", "E6": "기쁨",
}


def emotion_major_category(e_code: str) -> str:
    """E코드 앞자리로 6개 대분류 그룹핑"""
    prefix = e_code[:2]
    return EMOTION_MAJOR_PREFIX_MAP.get(prefix, "unknown")


# ============================================================
# 1. 파일 로드 (JSON array 형태, JSON Lines 형태 둘 다 방어)
# ============================================================

def load_json_flexible(path: str) -> list[dict]:
    """
    표준 JSON 배열([{...}, {...}])과, 객체가 콤마로만 이어진
    비표준 스트림 형태를 모두 처리한다.
    """
    text = Path(path).read_text(encoding="utf-8").strip()

    # 케이스 1: 표준 JSON
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # 케이스 2: 배열 대괄호 없이 객체가 콤마로만 이어진 경우
    fixed = f"[{text.rstrip(',')}]"
    return json.loads(fixed)


# ============================================================
# 2. 레코드 파싱 - HS01 + 감정 코드 추출
# ============================================================

def parse_records(records: list[dict]) -> tuple[pd.DataFrame, int]:
    rows = []
    skipped = 0

    for rec in records:
        try:
            profile = rec["profile"]
            human_codes = profile["persona"]["human"]  # ["A0x", "G0x"]
            age_code = next((c for c in human_codes if c.startswith("A")), None)
            gender_code = next((c for c in human_codes if c.startswith("G")), None)

            emo_type = profile["emotion"]["type"]  # 예: "E31"
            situation_codes = profile["emotion"].get("situation", [])

            hs01_text = rec["talk"]["content"].get("HS01")

            if hs01_text is None or age_code is None:
                skipped += 1
                continue

            rows.append({
                "profile_id": profile["persona-id"],
                "age_code": age_code,
                "age_label": AGE_CODE.get(age_code, "unknown"),
                "gender_code": gender_code,
                "gender_label": GENDER_CODE.get(gender_code, "unknown"),
                "situation_codes": situation_codes,
                "emotion_code": emo_type,
                "emotion_label": EMOTION_CODE.get(emo_type, "unknown"),
                "emotion_major": emotion_major_category(emo_type),
                "text": hs01_text,
            })
        except (KeyError, TypeError):
            skipped += 1
            continue

    return pd.DataFrame(rows), skipped


# ============================================================
# 3. 분포 리포트 출력
# ============================================================

def print_distribution_report(df: pd.DataFrame) -> None:
    print("=== 연령별 분포 ===")
    print(df["age_label"].value_counts())

    n_elderly = (df["age_code"] == "A04").sum()
    pct_elderly = (df["age_code"] == "A04").mean() * 100
    print(f"\n노년(A04) 건수: {n_elderly}건 / 비율: {pct_elderly:.2f}%")

    print("\n=== 성별 분포 ===")
    print(df["gender_label"].value_counts())

    print("\n=== 감정 대분류(6개) 분포 ===")
    print(df["emotion_major"].value_counts())

    print("\n=== 감정 세부(60개) 분포 (상위 20개) ===")
    print(df["emotion_label"].value_counts().head(20))

    elderly_df = df[df["age_code"] == "A04"]
    print(f"\n=== 노년층(A04, n={len(elderly_df)})만 필터링한 감정 세부 분포 ===")
    print(elderly_df["emotion_label"].value_counts())


# ============================================================
# 4. 검증 - 코드북 vs 실제 데이터 대조 (샘플 1건)
# ============================================================

def verify_sample(records: list[dict]) -> None:
    sample = records[0]
    emo_type = sample["profile"]["emotion"]["type"]
    hs01 = sample["talk"]["content"].get("HS01")
    print(f"[검증] 샘플 감정 코드: {emo_type} -> {EMOTION_CODE.get(emo_type, '코드북에 없음')}")
    print(f"[검증] 샘플 HS01: {hs01}")


# ============================================================
# 5. 산출물 저장
# ============================================================

def save_outputs(df: pd.DataFrame, output_dir: str = ".") -> None:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    elderly_df = df[df["age_code"] == "A04"]
    elderly_path = out_dir / "elderly_subset_hs01.csv"
    elderly_df.to_csv(elderly_path, index=False, encoding="utf-8-sig")
    print(f"노년층 서브셋 {len(elderly_df)}건을 {elderly_path}로 저장했다.")

    full_path = out_dir / "full_hs01_emotion_pairs.csv"
    df[["profile_id", "age_code", "emotion_code", "emotion_label", "emotion_major", "text"]].to_csv(
        full_path, index=False, encoding="utf-8-sig"
    )
    print(f"전체 (text, 감정코드) 쌍 {len(df)}건을 {full_path}로 저장했다.")


# ============================================================
# 6. 메인 실행부
# ============================================================

def main():
    FILE_PATH = (
        "/Users/jm/Desktop/1_Project/0_충북대학교 석사 1학기/4_학회/260406_ICCAS/"
        "CalmChat/notebooks/018.감성대화/감성대화말뭉치(최종데이터)_Training.json"
    )

    records = load_json_flexible(FILE_PATH)
    print(f"총 레코드 수: {len(records)}")

    verify_sample(records)

    df, skipped = parse_records(records)
    print(f"\n파싱 성공: {len(df)}건 / 스킵: {skipped}건")

    print_distribution_report(df)
    save_outputs(df, output_dir="./output")


if __name__ == "__main__":
    main()