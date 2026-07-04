import React, { useRef, useState } from "react";
import {
  PermissionsAndroid,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import AudioRecord from "react-native-audio-record";
import RNFS from "react-native-fs";
import Sound from "react-native-sound";

import { AnimatedAvatar } from "../components/Avatar/AnimatedAvatar";
import { CalmButton } from "../components/ui/CalmButton";
import { CalmCard } from "../components/ui/CalmCard";
import { sendVoiceChat, updateProfile } from "../api/client";
import { colors } from "../theme/theme";

const PROFILE_UPDATE_TURN_INTERVAL = 4;

Sound.setCategory("Playback");

// 상태별 안내 문구 (아바타 위 제목) - 어르신께 지금 뭘 하고 있는지 바로 알려주는 용도
// const STATUS_TITLE = {
//   idle: "Tap the microphone to start talking",
//   listening: "I'm listening",
//   thinking: "I'm thinking about my response",
//   speaking: "I'm responding",
// };

// 상태별 버튼 문구
const BUTTON_LABEL = {
  idle: "Tap to talk",
  listening: "Listening... tap to stop",
  thinking: "Thinking..",
  speaking: "Answering...",
};

export default function ChatScreen({ user, onRefreshMetrics, onRefreshRecentMessages }) {
  const [avatarState, setAvatarState] = useState("idle");
  const [lastResponse, setLastResponse] = useState("");
  const turnsSinceProfileUpdate = useRef(0);

  const isBusy = avatarState === "thinking" || avatarState === "speaking";

  const requestPermission = async () => {
    await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.RECORD_AUDIO);
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

  const maybeUpdateProfile = async () => {
    turnsSinceProfileUpdate.current += 1;
    if (turnsSinceProfileUpdate.current < PROFILE_UPDATE_TURN_INTERVAL) {
      return;
    }

    turnsSinceProfileUpdate.current = 0;
    try {
      await updateProfile(user.id);
    } catch (err) {
      console.warn("Profile refresh skipped:", err);
    }
  };

  const playBase64Audio = async (audioBase64, contentType = "audio/wav") => {
    if (!audioBase64) {
      return;
    }

    const extension = contentType.includes("mpeg") ? "mp3" : "wav";
    const filePath = `${RNFS.CachesDirectoryPath}/calmchat-tts-${Date.now()}.${extension}`;

    await RNFS.writeFile(filePath, audioBase64, "base64");

    await new Promise((resolve, reject) => {
      const sound = new Sound(filePath, "", (loadError) => {
        if (loadError) {
          RNFS.unlink(filePath).catch(() => {});
          reject(loadError);
          return;
        }

        sound.play((success) => {
          sound.release();
          RNFS.unlink(filePath).catch(() => {});
          if (success) {
            resolve();
          } else {
            reject(new Error("TTS playback failed."));
          }
        });
      });
    });
  };

  const stopRecordingAndProcess = async () => {
    setAvatarState("thinking");

    try {
      const filePath = await AudioRecord.stop();

      const result = await sendVoiceChat(user.id, filePath);
      setLastResponse(result.response_text);

      await onRefreshMetrics?.({ retries: 3, delayMs: 500 });
      await onRefreshRecentMessages?.(); // 추가

      setAvatarState("speaking");

      await playBase64Audio(result.audio_base64, result.audio_content_type);
      
      maybeUpdateProfile();

    } catch (err) {
      console.error("Failed to process voice message:", err);
    } finally {
      setAvatarState("idle");
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>Chat</Text>

        <AnimatedAvatar state={avatarState} size={200} />

        <CalmCard style={styles.responseCard}>
          <Text style={styles.responseText}>
            {lastResponse || "Tap the microphone and start talking."}
          </Text>
        </CalmCard>

        <CalmButton
          title={BUTTON_LABEL[avatarState]}
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
    fontSize: 26,
    fontWeight: "700",
    color: colors.foreground,
    marginBottom: 16,
    textAlign: "center",
  },
  responseCard: {
    width: "100%",
    marginTop: 14,
    minHeight: 100,
    justifyContent: "center",
  },
  responseText: {
    fontSize: 20,
    lineHeight: 32,
    color: colors.foreground,
    textAlign: "center",
  },
  micButton: { width: "100%", marginTop: 28, minHeight: 72 },
  micIcon: { fontSize: 26 },
});