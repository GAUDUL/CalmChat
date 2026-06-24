import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  PermissionsAndroid,
} from "react-native";
import AudioRecord from "react-native-audio-record";

import { AnimatedAvatar } from "../components/Avatar/AnimatedAvatar";
import { CalmButton } from "../components/ui/CalmButton";
import { CalmCard } from "../components/ui/CalmCard";
import { colors } from "../theme/theme";
import { sendVoiceChat, fetchTTSAudio, updateProfile } from "../api/client";

export default function ChatScreen({ user }) {
  const [avatarState, setAvatarState] = useState("idle");
  const [lastResponse, setLastResponse] = useState("");

  const isBusy = avatarState === "thinking" || avatarState === "speaking";

  const requestPermission = async () => {
    await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.RECORD_AUDIO
    );
  };

  const startRecording = async () => {
    if (!user?.id) {
      return;
    }

    try {
      await requestPermission();

      AudioRecord.init({
        sampleRate: 16000,
        channels: 1,
        bitsPerSample: 16,
        wavFile: "voice.wav",
      });

      AudioRecord.start();
      setAvatarState("listening");
    } catch (err) {
      console.error("Failed to start recording:", err);
    }
  };

  const stopRecordingAndProcess = async () => {
    setAvatarState("thinking");

    try {
      const filePath = await AudioRecord.stop();

      // Server resolves STT + chat for the current device-backed user.
      const { response_text } = await sendVoiceChat(user.id, filePath);
      setLastResponse(response_text);

      setAvatarState("speaking");
      await fetchTTSAudio(
        user.id,
        response_text,
        Boolean(user.family_voice_enabled)
      );
      await updateProfile(user.id);
    } catch (err) {
      console.error("Failed to process voice message:", err);
    } finally {
      setAvatarState("idle");
    }
  };

  const buttonLabel =
    avatarState === "listening"
      ? "Listening... tap to stop"
      : avatarState === "thinking"
      ? "Thinking..."
      : avatarState === "speaking"
      ? "Answering..."
      : "Tap to talk";

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>Chat</Text>

        <AnimatedAvatar state={avatarState} size={160} />

        <CalmCard style={styles.responseCard}>
          <Text style={styles.responseText}>
            {lastResponse || "Tap the microphone and start talking."}
          </Text>
        </CalmCard>

        <CalmButton
          title={buttonLabel}
          icon={<Text style={styles.micIcon}>🎤</Text>}
          variant={avatarState === "listening" ? "accent" : "primary"}
          disabled={isBusy || !user?.id}
          onPress={
            avatarState === "listening"
              ? stopRecordingAndProcess
              : startRecording
          }
          style={styles.micButton}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  container: { padding: 20, alignItems: "center", flex: 1 },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.foreground,
    marginBottom: 16,
  },
  responseCard: {
    width: "100%",
    marginTop: 24,
    minHeight: 90,
    justifyContent: "center",
  },
  responseText: {
    fontSize: 17,
    lineHeight: 24,
    color: colors.foreground,
    textAlign: "center",
  },
  micButton: { width: "100%", marginTop: 28 },
  micIcon: { fontSize: 20 },
});
