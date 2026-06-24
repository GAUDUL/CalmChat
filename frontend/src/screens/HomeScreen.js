import React from "react";
import { View, Text, StyleSheet, ScrollView, SafeAreaView } from "react-native";
import { AnimatedAvatar } from "../components/Avatar/AnimatedAvatar";
import { CalmButton } from "../components/ui/CalmButton";
import { CalmCard } from "../components/ui/CalmCard";
import { colors, typography } from "../theme/theme";

export default function HomeScreen({ onNavigate }) {
  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        {/* TODO: CalmChat의 logoAsset처럼 실제 로고 이미지로 교체 */}
        <Text style={styles.logo}>CalmChat</Text>

        <AnimatedAvatar state="idle" size={140} />

        <Text style={styles.greeting}>
          Hello.{"\n"}Would you like to talk with me today?
        </Text>
        <Text style={styles.subGreeting}>I am always here with you.</Text>

        <CalmCard warm style={styles.heroCard}>
          <Text style={styles.cardText}>
            <Text style={styles.cardTextBold}>Hello, my friend.</Text> I am
            happy to spend time with you today. When you are ready, tap below.
          </Text>
        </CalmCard>

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
