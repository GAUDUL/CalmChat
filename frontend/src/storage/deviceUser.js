import RNFS from "react-native-fs";

const DEVICE_USER_FILE = `${RNFS.DocumentDirectoryPath}/calmchat-device.json`;

function createDeviceKey() {
  // This is not authentication; it is a stable local handle for matching this install to users.id.
  const randomPart = Math.random().toString(36).slice(2);
  return `device-${Date.now()}-${randomPart}`;
}

export async function getOrCreateDeviceKey() {
  try {
    // Reuse the same key across app restarts so server-side history stays attached.
    const exists = await RNFS.exists(DEVICE_USER_FILE);
    if (exists) {
      const raw = await RNFS.readFile(DEVICE_USER_FILE, "utf8");
      const parsed = JSON.parse(raw);
      if (parsed.deviceKey) {
        return parsed.deviceKey;
      }
    }
  } catch (err) {
    console.warn("Failed to read device key:", err);
  }

  const deviceKey = createDeviceKey();
  await RNFS.writeFile(
    DEVICE_USER_FILE,
    JSON.stringify({ deviceKey }),
    "utf8"
  );
  return deviceKey;
}
