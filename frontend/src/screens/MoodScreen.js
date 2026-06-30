import React, { useEffect } from "react";
import {
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { CalmCard } from "../components/ui/CalmCard";
import { colors } from "../theme/theme";

export default function MoodScreen({
  user,
  metrics,
  metricsLoading,
  metricsError,
  onRefreshMetrics,
}) {
  const emotionScore = metrics?.emotion_score ?? 50;
  const energyScore = metrics?.energy_score ?? 50;

  useEffect(() => {
    if (!user?.id) {
      return;
    }

    // Mood 진입 시 최신 점수 요청.
    onRefreshMetrics?.();
  }, [onRefreshMetrics, user?.id]);

  const showLoading = metricsLoading && !metrics;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Today's Mood</Text>

        {showLoading ? (
          <ActivityIndicator size="large" color={colors.primary} />
        ) : metricsError ? (
          <CalmCard style={styles.card}>
            <Text style={styles.label}>{metricsError}</Text>
          </CalmCard>
        ) : (
          <>
            <CalmCard style={styles.card}>
              <Text style={styles.label}>Emotion score</Text>
              <Text style={styles.value}>{emotionScore}</Text>
            </CalmCard>

            <CalmCard style={styles.card}>
              <Text style={styles.label}>Energy score</Text>
              <Text style={styles.value}>{energyScore}</Text>
            </CalmCard>

            {metrics?.anomaly_detected && (
              <CalmCard warm style={styles.card}>
                <Text style={styles.alertLabel}>A change was detected</Text>
                <Text style={styles.label}>{metrics.recommended_solution}</Text>
              </CalmCard>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  container: {
    padding: 20,
    alignItems: "stretch",
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
  card: { width: "100%" },
  label: { fontSize: 15, color: colors.mutedForeground },
  value: {
    fontSize: 28,
    fontWeight: "700",
    color: colors.primary,
    marginTop: 4,
  },
  alertLabel: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.accent,
    marginBottom: 4,
  },
});
