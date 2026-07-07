"""
kote44_lift_analysis.py

[목적]
kote44_cluster_baserate.csv / kote44_cluster_hitrate.csv를 그대로 읽어서
lift = hit_rate / base_rate(gold_cluster) 를 계산한다.

hit-rate만 보면 base rate가 원래 높은 클러스터(슬픔_상실 64%, 불안_긴장 59%)는
어떤 문장을 넣어도 우연히 hit-rate가 높게 나오므로, "모델이 진짜 이 감정을
인식해서 맞춘 것"과 "그 클러스터가 원래 자주 뜨는 것뿐"을 구분해야 한다.

lift > 1: base rate보다 유의미하게 더 자주 맞음 -> 진짜 신호
lift ~ 1: base rate만큼만 맞음 -> 사실상 랜덤
lift < 1: base rate보다도 못 맞음 -> 모델이 오히려 그 코드를 다른 클러스터로 착각하는 역신호

모델 재실행 없이 저장된 CSV 두 개만으로 계산 (빠름).
"""

import pandas as pd

BASERATE_PATH = "./kote44_cluster_baserate.csv"
HITRATE_PATH = "./kote44_cluster_hitrate.csv"


def main():
    base_df = pd.read_csv(BASERATE_PATH)
    hit_df = pd.read_csv(HITRATE_PATH)

    base_map = dict(zip(base_df["cluster"], base_df["base_rate"]))

    hit_df["base_rate"] = hit_df["gold_cluster"].map(base_map)
    hit_df["lift"] = hit_df["hit_rate"] / hit_df["base_rate"]

    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 120)

    print("===== 전체 코드 lift (오름차순 = 모델이 가장 못 잡는 코드부터) =====")
    print(
        hit_df[["emotion_code", "gold_cluster", "hit_rate", "base_rate", "lift", "n"]]
        .sort_values("lift")
        .to_string(index=False)
    )

    print("\n===== [핵심] lift < 1.2 인 코드 (사실상 랜덤 이하 - 모델이 인식 못 함) =====")
    weak = hit_df[hit_df["lift"] < 1.2].sort_values("lift")
    print(weak[["emotion_code", "gold_cluster", "hit_rate", "base_rate", "lift", "n"]].to_string(index=False))

    print("\n===== [참고] lift > 2 인 코드 (base rate 대비 확실한 신호) =====")
    strong = hit_df[hit_df["lift"] > 2].sort_values("lift", ascending=False)
    print(strong[["emotion_code", "gold_cluster", "hit_rate", "base_rate", "lift", "n"]].to_string(index=False))

    hit_df.to_csv("./kote44_lift_analysis.csv", index=False, encoding="utf-8-sig")
    print("\n결과 저장 완료: ./kote44_lift_analysis.csv")


if __name__ == "__main__":
    main()
