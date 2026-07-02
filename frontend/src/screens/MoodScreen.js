import React, { useEffect } from "react";
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { CalmCard } from "../components/ui/CalmCard";
import { colors } from "../theme/theme";
import * as Progress from "react-native-progress";
import { Dimensions } from "react-native";
import { LineChart } from "react-native-chart-kit";

export default function MoodScreen({
  user,
  metrics,
  metricsLoading,
  metricsError,
  onRefreshMetrics,
}) {
  const screenWidth = Dimensions.get("window").width;
  const emotionScore = metrics?.emotion_score ?? "-";
  const energyScore = metrics?.energy_score ?? "-";
  
  const riskLabelMap = {
    caution: "Caution",
    warning: "Warning",
    danger: "Danger",
  };

  const riskLabel =
    riskLabelMap[metrics?.risk_level] ?? "Change Detected";

  useEffect(() => {
    if (!user?.id) {
      return;
    }

    onRefreshMetrics?.();
  }, [onRefreshMetrics, user?.id]);

  const showLoading = metricsLoading && !metrics;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Today's Mood</Text>

        {showLoading ? (
          <View style={styles.centerBox}>
            <ActivityIndicator
              size="large"
              color={colors.primary}
            />
            <Text style={styles.loadingText}>
              Loading your mood metrics...
            </Text>
          </View>
        ) : metricsError ? (
          <CalmCard style={styles.card}>
            <Text style={styles.errorText}>
              {metricsError}
            </Text>
          </CalmCard>
        ) : (
          <>
            <View style={styles.scoreRow}>
              <CalmCard style={styles.scoreCard}>
                <Text style={styles.label}>
                  Emotion Score
                </Text>

                <Progress.Circle
                  progress={Number(emotionScore) / 100}
                  size={120}
                  thickness={10}
                  showsText
                  formatText={() => String(emotionScore)}
                  color={colors.primary}
                  textStyle={styles.progressText}
                />
              </CalmCard>

              <CalmCard style={styles.scoreCard}>
                <Text style={styles.label}>
                  Energy Score
                </Text>

                <Progress.Circle
                  progress={Number(energyScore) / 100}
                  size={120}
                  thickness={10}
                  showsText
                  formatText={() => String(energyScore)}
                  color={colors.primary}
                  textStyle={styles.progressText}
                />
              </CalmCard>
            </View>
            {metrics?.weekly_trend?.length > 0 && (
              <CalmCard style={styles.card}>
                <Text style={styles.label}>
                  Weekly Mood Trend
                </Text>
                <LineChart
                  data={{
                    labels: metrics.weekly_trend.map(item =>
                      item.date.slice(5)
                    ),
                    datasets: [
                      {
                        data: metrics.weekly_trend.map(
                          item => item.emotion_score ?? 0
                        ),
                      },
                    ],
                  }}
                  width={screenWidth - 80}
                  height={220}
                  chartConfig={{
                    decimalPlaces: 0,
                    backgroundGradientFrom: colors.card,
                    backgroundGradientTo: colors.card,
                    color: opacity =>
                      `rgba(94,129,172,${opacity})`,
                    labelColor: opacity =>
                      `rgba(120,120,120,${opacity})`,
                  }}
                  bezier
                  style={{
                    marginTop: 12,
                    borderRadius: 12,
                    alignSelf: "center",
                  }}
                />
              </CalmCard>
            )}
            {metrics?.anomaly_detected ? (
              <CalmCard warm style={styles.card}>
                <Text style={styles.alertTitle}>
                  ⚠️ {riskLabel}
                </Text>

                <Text style={styles.description}>
                  {metrics?.recommended_solution ??
                    "Take a short break and give yourself some time to rest."}
                </Text>
              </CalmCard>
            ) : (
              <CalmCard style={styles.card}>
                <Text style={styles.label}>
                  Current Status
                </Text>

                <Text style={styles.normalText}>
                  🟢 Stable
                </Text>

                <Text style={styles.description}>
                  No significant changes have been detected.
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
    fontSize: 26,
    fontWeight: "700",
    color: colors.foreground,
    marginBottom: 8,
    textAlign: "center",
  },

  label: {
    fontSize: 19,
    fontWeight: "600", 
    color: colors.mutedForeground,
  },

  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: colors.mutedForeground,
    textAlign: "center",
  },

  description: {
    fontSize: 18,
    color: colors.mutedForeground,
    lineHeight: 26,
  },

  alertTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: colors.accent,
    marginBottom: 8,
  },

  errorText: {
    fontSize: 17, 
    color: colors.mutedForeground,
  },

  scoreRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 14,
  },

  scoreCard: {
    flex: 1,
    alignItems: "center",
    gap: 16,
  },

  normalText: {
    fontSize: 20,
    fontWeight: "700",
    color: colors.foreground,
    marginTop: 6,
  },

  progressText: {
  fontSize: 24,
  fontWeight: "500",
  },
});