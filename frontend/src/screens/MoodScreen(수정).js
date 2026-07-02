import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { CalmCard } from "../components/ui/CalmCard";
import { fetchMetrics } from "../api/client";
import { colors } from "../theme/theme";

const CURRENT_USER_ID = 1;

export default function MoodScreen() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    async function loadMetrics() {
      try {
        setLoading(true);
        setError(null);

        const data = await fetchMetrics(CURRENT_USER_ID);

        if (alive) {
          setMetrics(data);
        }
      } catch (err) {
        console.error("지표 조회 실패:", err);

        if (alive) {
          setError("지표를 불러오지 못했어요.");
        }
      } finally {
        if (alive) {
          setLoading(false);
        }
      }
    }

    loadMetrics();

    return () => {
      alive = false;
    };
  }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>오늘의 기분</Text>

        {loading ? (
          <View style={styles.centerBox}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.loadingText}>기분 지표를 불러오는 중이에요.</Text>
          </View>
        ) : error ? (
          <CalmCard style={styles.card}>
            <Text style={styles.errorText}>{error}</Text>
          </CalmCard>
        ) : (
          <>
            <CalmCard style={styles.card}>
              <Text style={styles.label}>정서 점수</Text>
              <Text style={styles.value}>
                {metrics?.emotion_score ?? "-"}
              </Text>
            </CalmCard>

            <CalmCard style={styles.card}>
              <Text style={styles.label}>활력 점수</Text>
              <Text style={styles.value}>
                {metrics?.energy_score ?? "-"}
              </Text>
            </CalmCard>

            {metrics?.anomaly_detected ? (
              <CalmCard warm style={styles.card}>
                <Text style={styles.alertTitle}>변화가 감지되었어요</Text>
                <Text style={styles.description}>
                  {metrics?.recommended_solution ??
                    "잠시 편안한 자세로 쉬어가세요."}
                </Text>
              </CalmCard>
            ) : (
              <CalmCard style={styles.card}>
                <Text style={styles.label}>현재 상태</Text>
                <Text style={styles.normalText}>
                  큰 변화는 감지되지 않았어요.
                </Text>
              </CalmCard>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  },
  container: {
    padding: 20,
    paddingBottom: 40,
    gap: 14,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.foreground,
    marginBottom: 8,
    textAlign: "center",
  },
  card: {
    width: "100%",
  },
  centerBox: {
    paddingVertical: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: colors.mutedForeground,
    textAlign: "center",
  },
  label: {
    fontSize: 15,
    color: colors.mutedForeground,
  },
  value: {
    fontSize: 32,
    fontWeight: "700",
    color: colors.primary,
    marginTop: 6,
  },
  alertTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.accent,
    marginBottom: 6,
  },
  description: {
    fontSize: 15,
    color: colors.mutedForeground,
    lineHeight: 22,
  },
  normalText: {
    fontSize: 17,
    fontWeight: "600",
    color: colors.foreground,
    marginTop: 6,
  },
  errorText: {
    fontSize: 15,
    color: colors.mutedForeground,
  },
});
