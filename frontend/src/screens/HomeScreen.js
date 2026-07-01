import React from "react";
import { View, Text, StyleSheet, ScrollView, SafeAreaView } from "react-native";
import { AnimatedAvatar } from "../components/Avatar/AnimatedAvatar";
import { CalmButton } from "../components/ui/CalmButton";
import { CalmCard } from "../components/ui/CalmCard";
import { colors, typography } from "../theme/theme";

export default function HomeScreen({
  onNavigate,
  user,
  metrics,
  recentMessages = [],
}) {
  const riskLabelMap = {
    caution: "Caution",
    warning: "Warning",
    danger: "Danger",
  };
  const riskLabel = riskLabelMap[metrics?.risk_level];

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.logo}>CalmChat</Text>

        <AnimatedAvatar state="idle" size={140} />

        <Text style={styles.greeting}>
          Hello.{"\n"}Would you like to talk with me today?
        </Text>

        <Text style={styles.subGreeting}>
          I am always here with you.
        </Text>

        {/* BUTTONS */}
        <View style={styles.buttonGroup}>
          <CalmButton
            title="Start chatting"
            icon={<Text style={styles.buttonIcon}>🎤</Text>}
            variant="primary"
            onPress={() => onNavigate("Chat")}
            style={styles.fullWidthButton}
          />

          <CalmButton
            title="Check today's mood"
            icon={<Text style={styles.buttonIconGhost}>🙂</Text>}
            variant="ghost"
            onPress={() => onNavigate("Mood")}
            style={styles.fullWidthButton}
          />
        </View>
        
        {/* STATUS CARD */}
        <CalmCard warm style={styles.heroCard}>
          <Text style={styles.cardText}>
            <Text style={styles.cardTextBold}>Status</Text>{"\n"}
            Emotion: {metrics?.emotion_score ?? "-"}{"\n"}
            Energy: {metrics?.energy_score ?? "-"}
            {riskLabel ? `\nRisk level: ${riskLabel}` : ""}
          </Text>
        </CalmCard>

        {/* RECENT */}
        <View style={{ width: "100%", marginTop: 24 }}>
          <Text style={{ fontSize: 18, fontWeight: "700", marginBottom: 10 }}>
            Recent Conversations
          </Text>

          {recentMessages.length === 0 ? (
            <Text style={{ color: "#888" }}>No conversations yet</Text>
          ) : (
            recentMessages.map((item) => (
              <View
                key={item.id}
                style={{
                  padding: 12,
                  borderRadius: 10,
                  backgroundColor: "#fff",
                  marginBottom: 8,
                }}
              >
                <Text numberOfLines={1} style={{ fontSize: 15 }}>
                  {item.content}
                </Text>

                <Text style={{ fontSize: 12, color: "#888", marginTop: 4 }}>
                  {item.role}
                </Text>
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surfaceWarm },
  container: { padding: 20, alignItems: "center", paddingBottom: 40 },
  logo: {
    fontSize: 22,
    fontWeight: "800",
    color: colors.primary,
    marginBottom: 12,
  },
  greeting: {
    fontSize: typography.h2,
    fontWeight: "700",
    textAlign: "center",
    color: colors.foreground,
    marginTop: 20,
  },
  subGreeting: {
    fontSize: 17,
    color: colors.mutedForeground,
    marginTop: 8,
    textAlign: "center",
  },
  heroCard: { marginTop: 24, width: "100%" },
  cardText: { fontSize: 17, lineHeight: 24, color: colors.foreground },
  cardTextBold: { fontWeight: "700" },
  buttonGroup: { marginTop: 28, width: "100%", gap: 14 },
  fullWidthButton: { width: "100%" },
  buttonIcon: { fontSize: 20 },
  buttonIconGhost: { fontSize: 20 },
});
