import React, { useEffect, useState } from "react";
import {
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { CalmCard } from "../components/ui/CalmCard";
import { colors } from "../theme/theme";
import { fetchMetrics } from "../api/client";

export default function MoodScreen({ user }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user?.id) {
      return;
    }

    setLoading(true);
    setError(null);

    // Mood metrics are scoped by the user row created for this device.
    fetchMetrics(user.id)
      .then(setMetrics)
      .catch((err) => {
        console.error("Failed to load metrics:", err);
        setError("Could not load your mood data.");
      })
      .finally(() => setLoading(false));
  }, [user?.id]);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Today's Mood</Text>

        {loading ? (
          <ActivityIndicator size="large" color={colors.primary} />
        ) : error ? (
          <CalmCard style={styles.card}>
            <Text style={styles.label}>{error}</Text>
          </CalmCard>
        ) : (
          <>
            <CalmCard style={styles.card}>
              <Text style={styles.label}>Emotion score</Text>
              <Text style={styles.value}>{metrics?.emotion_score ?? "-"}</Text>
            </CalmCard>

            <CalmCard style={styles.card}>
              <Text style={styles.label}>Energy score</Text>
              <Text style={styles.value}>{metrics?.energy_score ?? "-"}</Text>
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
