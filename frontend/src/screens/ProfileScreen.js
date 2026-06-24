import React, { useEffect, useState } from "react";
import { View, Text, Switch, StyleSheet, SafeAreaView, ScrollView } from "react-native";
import { CalmCard } from "../components/ui/CalmCard";
import { updateUserPreferences } from "../api/client";
import { colors } from "../theme/theme";

export default function ProfileScreen({ user, onUserChange }) {
  const [familyVoiceEnabled, setFamilyVoiceEnabled] = useState(
    Boolean(user?.family_voice_enabled)
  );

  useEffect(() => {
    setFamilyVoiceEnabled(Boolean(user?.family_voice_enabled));
  }, [user?.family_voice_enabled]);

  const handleFamilyVoiceChange = async (enabled) => {
    setFamilyVoiceEnabled(enabled);

    try {
      // Persist profile preferences on the same users row used by chat and mood.
      const updatedUser = await updateUserPreferences(user.id, {
        family_voice_enabled: enabled,
      });
      onUserChange(updatedUser);
    } catch (err) {
      console.error("Failed to update user preferences:", err);
      setFamilyVoiceEnabled(!enabled);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>My Profile</Text>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>Name</Text>
          <Text style={styles.value}>{user?.name || "CalmChat User"}</Text>
        </CalmCard>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>Phone</Text>
          <Text style={styles.value}>{user?.phone || "-"}</Text>
        </CalmCard>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>Region</Text>
          <Text style={styles.value}>{user?.region_dialect || "-"}</Text>
        </CalmCard>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>User ID</Text>
          <Text style={styles.value}>{user?.id ?? "-"}</Text>
        </CalmCard>

        <CalmCard style={[styles.card, styles.row]}>
          <View style={styles.rowText}>
            <Text style={styles.label}>Use family voice</Text>
            <Text style={styles.helper}>
              When enabled, replies will use the registered family voice.
            </Text>
          </View>
          <Switch
            value={familyVoiceEnabled}
            onValueChange={handleFamilyVoiceChange}
            disabled={!user?.id}
            trackColor={{ true: colors.primary, false: colors.border }}
          />
        </CalmCard>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  container: { padding: 20, gap: 14, paddingBottom: 40 },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.foreground,
    marginBottom: 8,
    textAlign: "center",
  },
  card: { width: "100%" },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  rowText: { flexShrink: 1 },
  label: { fontSize: 17, fontWeight: "600", color: colors.foreground },
  value: { fontSize: 18, color: colors.foreground, marginTop: 4 },
  helper: {
    fontSize: 13,
    color: colors.mutedForeground,
    marginTop: 2,
    maxWidth: 220,
  },
});
