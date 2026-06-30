import axios from "axios";
import { Platform } from "react-native";
import { API_BASE_URL } from "@env";
import { getOrCreateDeviceKey } from "../storage/deviceUser";

// Android emulator cannot reach the host machine through localhost.
// Use 10.0.2.2 for Android emulator; use the PC LAN IP for a physical phone.
const BASE_URL = API_BASE_URL || (
  Platform.OS === "android"
    ? "http://10.0.2.2:8000"
    : "http://localhost:8000"
);

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
});

api.interceptors.request.use(async (config) => {
  const deviceKey = await getOrCreateDeviceKey();
  return {
    ...config,
    headers: {
      ...config.headers,
      "X-Device-Key": deviceKey,
    },
  };
});

export async function registerDeviceUser(deviceKey) {
  const { data } = await api.post("/users/device", {
    device_key: deviceKey,
  });
  return data;
}

export async function updateUserPreferences(userId, preferences) {
  const { data } = await api.patch(`/users/${userId}`, preferences);
  return data;
}

// 테스트용 (현재 사용 X)
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
  return data;
}

export async function sendChatMessage(userId, text) {
  const { data } = await api.post("/chat", { user_id: userId, text });
  return data;
}

export async function sendVoiceChat(userId, audioUri) {
  const formData = new FormData();
  formData.append("user_id", String(userId));
  formData.append("audio", {
    uri: `file://${audioUri}`,
    name: "recording.wav",
    type: "audio/wav",
  });

  const { data } = await api.post("/chat/audio", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 90000,
  });
  return data;
}

export async function fetchTTSAudio(userId, text, useFamilyVoice = false) {
  const response = await api.post(
    "/tts",
    { user_id: userId, text, use_family_voice: useFamilyVoice },
    {
      responseType: "arraybuffer",
      // XTTS cloning can be slow on CPU, so do not use the global 15s timeout.
      timeout: 90000,
    }
  );
  return response.data;
}

export async function setFamilyVoiceEnabled(userId, enabled) {
  const { data } = await api.patch("/tts/family/enabled", {
    user_id: userId,
    enabled,
  });
  return data;
}

export async function uploadFamilyVoice(userId, familyMemberName, audioUri) {
  const formData = new FormData();
  formData.append("user_id", String(userId));
  formData.append("family_member_name", familyMemberName);
  formData.append("audio", {
    uri: Platform.OS === "android" ? audioUri : `file://${audioUri}`,
    name: "family_voice.wav",
    type: "audio/wav",
  });

  const { data } = await api.post("/tts/family/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000,
  });
  return data;
}

export async function updateProfile(userId) {
  const { data } = await api.post("/profile/update", { user_id: userId });
  return data;
}

export async function fetchMetrics(userId) {
  const { data } = await api.get(`/metrics/${userId}`);
  return data;
}

export async function fetchRecentMessages(userId) {
  const { data } = await api.get("/home/recent-messages", {
    params: {
      user_id: userId,
    },
  });

  return data;
}

export default api;
