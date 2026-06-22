import React, { useState } from "react";
import { View, Text, StyleSheet, SafeAreaView, PermissionsAndroid } from "react-native";
import AudioRecord from "react-native-audio-record";

import { AnimatedAvatar } from "../components/Avatar/AnimatedAvatar";
import { CalmButton } from "../components/ui/CalmButton";
import { CalmCard } from "../components/ui/CalmCard";
import { colors } from "../theme/theme";
import {
  sendAudioForSTT,
  sendChatMessage,
  fetchTTSAudio,
  updateProfile,
} from "../api/client";

// TODO: 실제 로그인/사용자 식별 로직으로 교체
const CURRENT_USER_ID = 1;

// avatarState: "idle" | "listening" | "thinking" | "speaking"
// 화면 흐름도: 음성버튼 탭(listening) -> STT/LLM(thinking) -> TTS 재생(speaking) -> 이력저장 -> idle
//
// RN CLI 환경에서는 react-native-audio-record 기반으로 녹음 처리합니다.
export default function ChatScreen() {
  const [avatarState, setAvatarState] = useState("idle");
  const [lastResponse, setLastResponse] = useState("");
  const [audioFile, setAudioFile] = useState(null);

  const isBusy = avatarState === "thinking" || avatarState === "speaking";

  const requestPermission = async () => {
    await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.RECORD_AUDIO
    );
  };

  const startRecording = async () => {
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
      console.error("녹음 시작 실패:", err);
    }
  };

  const stopRecordingAndProcess = async () => {
    setAvatarState("thinking");

    try {
      const filePath = await AudioRecord.stop();
      setAudioFile(filePath);

      // 1) STT (서버로 파일 업로드)
      const { text } = await sendAudioForSTT(filePath);

      // 2) Chat
      const { response_text } = await sendChatMessage(
        CURRENT_USER_ID,
        text
      );

      setLastResponse(response_text);

      // 3) TTS
      setAvatarState("speaking");

      const audioBytes = await fetchTTSAudio(
        CURRENT_USER_ID,
        response_text
      );

      // TODO: 재생 로직 (react-native-sound or native module)

      await updateProfile(CURRENT_USER_ID);

    } catch (err) {
      console.error("음성 처리 오류:", err);
    } finally {
      setAvatarState("idle");
    }
  };

  const buttonLabel =
    avatarState === "listening"
      ? "말하는 중... (눌러서 종료)"
      : avatarState === "thinking"
      ? "생각하는 중..."
      : avatarState === "speaking"
      ? "대답하는 중..."
      : "눌러서 말하기";

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>대화하기</Text>

        <AnimatedAvatar state={avatarState} size={160} />

        <CalmCard style={styles.responseCard}>
          <Text style={styles.responseText}>
            {lastResponse || "마이크를 눌러 이야기를 시작해보세요."}
          </Text>
        </CalmCard>

        <CalmButton
          title={buttonLabel}
          icon={<Text style={styles.micIcon}>🎤</Text>}
          variant={avatarState === "listening" ? "accent" : "primary"}
          disabled={isBusy}
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