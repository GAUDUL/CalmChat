import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  Switch,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Alert,
  Platform,
} from "react-native";
// Updated import to the new stable package
import { pick, isCancel, types } from "@react-native-documents/picker";

import { CalmCard } from "../components/ui/CalmCard";
import { CalmButton } from "../components/ui/CalmButton";

import {
  setFamilyVoiceEnabled as apiSetFamilyVoiceEnabled,
  uploadFamilyVoice,
} from "../api/client";

import { colors } from "../theme/theme";

export default function ProfileScreen({ user, onUserChange }) {
  const [familyVoiceEnabled, setFamilyVoiceEnabledState] = useState(
    Boolean(user?.family_voice_enabled)
  );

  const [isUploading, setIsUploading] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState(null);

  useEffect(() => {
    setFamilyVoiceEnabledState(Boolean(user?.family_voice_enabled));
  }, [user?.family_voice_enabled]);

  const handleFamilyVoiceChange = async (enabled) => {
    setFamilyVoiceEnabledState(enabled);

    try {
      if (!user?.id) {
        throw new Error("User not found");
      }

      await apiSetFamilyVoiceEnabled(user.id, enabled);

      onUserChange({
        ...user,
        family_voice_enabled: enabled,
      });
    } catch (err) {
      console.error("Failed to update user preferences:", err);

      setFamilyVoiceEnabledState(!enabled);

      Alert.alert(
        "Error",
        err?.response?.data?.detail ??
          "Failed to update family voice settings."
      );
    }
  };

  const handleUploadFamilyVoice = async () => {
    try {
      if (!user?.id) {
        Alert.alert("Error", "User not found.");
        return;
      }

      // Using the new pick method from @react-native-documents/picker
      // This package is compatible with newer React Native versions
      const [file] = await pick({
        type: [types.audio],
      });

      if (!file?.uri) return;

      setIsUploading(true);

      // Handle URI for both Android and iOS
      const fileToUpload = {
        uri: Platform.OS === 'android' ? file.uri : file.uri.replace('file://', ''),
        type: file.type || 'audio/mpeg',
        name: file.name || 'family_voice.mp3',
      };

      // uploadFamilyVoice is expected to handle the FormData upload
      await uploadFamilyVoice(
        user.id,
        "Family",
        fileToUpload
      );

      setSelectedFileName(file.name);

      Alert.alert(
        "Upload Complete",
        "Family voice has been registered successfully."
      );
    } catch (err) {
      if (isCancel(err)) {
        console.log("User cancelled the picker");
        return;
      }

      console.error("Family voice upload failed:", err);

      Alert.alert(
        "Error",
        err?.response?.data?.detail ??
          "Failed to upload family voice. Please check the file format."
      );
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>My Profile</Text>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>Name</Text>
          <Text style={styles.value}>
            {user?.name || "CalmChat User"}
          </Text>
        </CalmCard>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>Phone</Text>
          <Text style={styles.value}>
            {user?.phone || "-"}
          </Text>
        </CalmCard>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>Region</Text>
          <Text style={styles.value}>
            {user?.region_dialect || "-"}
          </Text>
        </CalmCard>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>User ID</Text>
          <Text style={styles.value}>
            {user?.id ?? "-"}
          </Text>
        </CalmCard>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>Family Voice</Text>

          <Text style={styles.helperFull}>
            Upload a voice recording of your family member.
          </Text>

          <Text style={styles.uploadGuide}>
            Recommended: 10-30 seconds of clear speech (MP3, WAV, etc.)
          </Text>

          <View style={styles.buttonWrapper}>
            <CalmButton
              title={isUploading ? "Uploading..." : "Upload Voice File"}
              onPress={handleUploadFamilyVoice}
              disabled={isUploading}
            />
          </View>

          {selectedFileName && (
            <Text style={styles.fileName}>
              Selected file: {selectedFileName}
            </Text>
          )}
        </CalmCard>

        <CalmCard style={[styles.card, styles.row]}>
          <View style={styles.rowText}>
            <Text style={styles.label}>
              Use family voice
            </Text>

            <Text style={styles.helper}>
              When enabled, replies will use the registered family voice.
            </Text>
          </View>

          <Switch
            value={familyVoiceEnabled}
            onValueChange={handleFamilyVoiceChange}
            disabled={!user?.id}
            trackColor={{
              true: colors.primary,
              false: colors.border,
            }}
          />
        </CalmCard>
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
    gap: 14,
    paddingBottom: 40,
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

  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  rowText: {
    flexShrink: 1,
  },

  label: {
    fontSize: 17,
    fontWeight: "600",
    color: colors.foreground,
  },

  value: {
    fontSize: 18,
    color: colors.foreground,
    marginTop: 4,
  },

  helper: {
    fontSize: 13,
    color: colors.mutedForeground,
    marginTop: 2,
    maxWidth: 220,
  },

  helperFull: {
    fontSize: 13,
    color: colors.mutedForeground,
    marginTop: 8,
  },

  uploadGuide: {
    fontSize: 13,
    color: colors.mutedForeground,
    marginTop: 4,
  },

  buttonWrapper: {
    marginTop: 16,
  },

  fileName: {
    marginTop: 12,
    fontSize: 13,
    color: colors.primary,
  },
});
