import axios from "axios";
import { Platform } from "react-native";

// TODO: 실제 백엔드 주소로 교체 (예: http://192.168.0.10:8000)
// Android emulator cannot reach the host machine through localhost.
// Use 10.0.2.2 for Android emulator; use the PC LAN IP for a physical phone.
const BASE_URL =
  Platform.OS === "android" ? "http://10.0.2.2:8000" : "http://localhost:8000";

const api = axios.create({ baseURL: BASE_URL, timeout: 15000 });

export async function registerDeviceUser(deviceKey) {
  const { data } = await api.post("/users/device", {
    device_key: deviceKey,
  });
  return data; // { id, name, device_key, family_voice_enabled, created_at }
}

export async function updateUserPreferences(userId, preferences) {
  const { data } = await api.patch(`/users/${userId}`, preferences);
  return data;
}

export async function sendAudioForSTT(audioUri) {
  const formData = new FormData();
  formData.append("audio", {
    uri: audioUri,
    name: "recording.wav",
    type: "audio/wav",
  });
  const { data } = await api.post("/stt", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data; // { text, confidence }
}

export async function sendChatMessage(userId, text) {
  const { data } = await api.post("/chat", { user_id: userId, text });
  return data; // { response_text, used_context }
}

export async function sendVoiceChat(userId, audioUri) {
  const formData = new FormData();
  formData.append("user_id", String(userId));
  // android 용 file url
  formData.append("audio", {
    uri: `file://${audioUri}`, // 변경
    name: "recording.wav",
    type: "audio/wav",
  });

  const { data } = await api.post("/chat/audio", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000,
  });
  return data; // { text, confidence, response_text, used_context, audio_base64 }
}

export async function fetchTTSAudio(userId, text, useFamilyVoice = false) {
  const response = await api.post(
    "/tts",
    { user_id: userId, text, use_family_voice: useFamilyVoice },
    { responseType: "arraybuffer" }
  );
  return response.data; // raw audio bytes
}

export async function updateProfile(userId) {
  const { data } = await api.post("/profile/update", { user_id: userId });
  return data;
}

export async function fetchMetrics(userId) {
  const { data } = await api.get(`/metrics/${userId}`);
  return data; // { emotion_score, energy_score, anomaly_detected, recommended_solution }
}

export default api;
