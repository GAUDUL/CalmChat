import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { CalmButton } from "../components/ui/CalmButton";
import { CalmCard } from "../components/ui/CalmCard";
import { updateUserPreferences } from "../api/client";
import { colors } from "../theme/theme";

export default function OnboardingScreen({ user, onComplete }) {
  // This is intentionally a short setup form instead of a full signup/login screen.
  const [name, setName] = useState(user?.name === "CalmChat User" ? "" : user?.name || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [region, setRegion] = useState(user?.region_dialect || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const canSubmit =
    name.trim().length > 0 &&
    phone.trim().length > 0 &&
    region.trim().length > 0 &&
    !saving;

  const handleSubmit = async () => {
    if (!canSubmit) {
      setError("Please fill in all fields.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // Fill the existing device-created users row with the profile fields needed by the app.
      const updatedUser = await updateUserPreferences(user.id, {
        name: name.trim(),
        phone: phone.trim() || null,
        region_dialect: region.trim() || null,
      });
      onComplete(updatedUser);
    } catch (err) {
      console.error("Failed to save onboarding profile:", err);
      const status = err?.response?.status;
      setError(
        status === 409
          ? "This phone number is already registered."
          : "Could not save your profile."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.keyboard}
      >
        <ScrollView contentContainerStyle={styles.container}>
          <Text style={styles.logo}>CalmChat</Text>
          <Text style={styles.title}>Tell us about this user</Text>
          <Text style={styles.subtitle}>
            This helps CalmChat keep conversations and mood records connected to
            this device.
          </Text>

          <CalmCard style={styles.card}>
            <View style={styles.field}>
              <Text style={styles.label}>Name</Text>
              <TextInput
                value={name}
                onChangeText={setName}
                placeholder="Enter a name"
                placeholderTextColor={colors.mutedForeground}
                style={styles.input}
              />
            </View>

            <View style={styles.field}>
              <Text style={styles.label}>Phone</Text>
              <TextInput
                value={phone}
                onChangeText={setPhone}
                placeholder="Enter a phone number"
                placeholderTextColor={colors.mutedForeground}
                keyboardType="phone-pad"
                style={styles.input}
              />
            </View>

            <View style={styles.field}>
              <Text style={styles.label}>Region</Text>
              <TextInput
                value={region}
                onChangeText={setRegion}
                placeholder="Enter a region"
                placeholderTextColor={colors.mutedForeground}
                style={styles.input}
              />
            </View>

            {error ? <Text style={styles.error}>{error}</Text> : null}
          </CalmCard>

          <CalmButton
            title={saving ? "Saving..." : "Continue"}
            disabled={!canSubmit}
            onPress={handleSubmit}
            style={styles.button}
            icon={saving ? <ActivityIndicator color={colors.primaryForeground} /> : null}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  keyboard: { flex: 1 },
  container: { padding: 20, paddingBottom: 40 },
  logo: {
    fontSize: 22,
    fontWeight: "800",
    color: colors.primary,
    textAlign: "center",
    marginTop: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: colors.foreground,
    textAlign: "center",
    marginTop: 28,
  },
  subtitle: {
    fontSize: 16,
    lineHeight: 22,
    color: colors.mutedForeground,
    textAlign: "center",
    marginTop: 8,
    marginBottom: 24,
  },
  card: { gap: 16 },
  field: { gap: 8 },
  label: { fontSize: 15, fontWeight: "700", color: colors.foreground },
  input: {
    minHeight: 52,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    paddingHorizontal: 16,
    color: colors.foreground,
    backgroundColor: colors.surface,
    fontSize: 17,
  },
  error: { color: colors.destructive, fontSize: 14 },
  button: { width: "100%", marginTop: 24 },
});
