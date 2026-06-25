import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  View,
  Text,
  Pressable,
  StyleSheet,
  SafeAreaView,
} from "react-native";
import { colors } from "./src/theme/theme";
import HomeScreen from "./src/screens/HomeScreen";
import ChatScreen from "./src/screens/ChatScreen";
import MoodScreen from "./src/screens/MoodScreen";
import ProfileScreen from "./src/screens/ProfileScreen";
import OnboardingScreen from "./src/screens/OnboardingScreen";
import { registerDeviceUser } from "./src/api/client";
import { getOrCreateDeviceKey } from "./src/storage/deviceUser";

const TABS = [
  { key: "Home", label: "Home", icon: "🏠", Component: HomeScreen },
  { key: "Chat", label: "Chat", icon: "💬", Component: ChatScreen },
  { key: "Mood", label: "Mood", icon: "🙂", Component: MoodScreen },
  { key: "Profile", label: "Profile", icon: "👤", Component: ProfileScreen },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("Home");
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [userError, setUserError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function initializeUser() {
      try {
        // No-login identity flow: keep a local device key, then resolve it to a DB user.
        const deviceKey = await getOrCreateDeviceKey();
        const registeredUser = await registerDeviceUser(deviceKey);
        if (mounted) {
          setUser(registeredUser);
        }
      } catch (err) {
        console.error("Failed to initialize device user:", err);
        if (mounted) {
          setUserError("Could not prepare this device profile.");
        }
      } finally {
        if (mounted) {
          setLoadingUser(false);
        }
      }
    }

    initializeUser();
    return () => {
      mounted = false;
    };
  }, []);

  const ActiveScreen =
    TABS.find((tab) => tab.key === activeTab)?.Component || HomeScreen;
  const needsProfileSetup =
    // Keep the first-run experience lightweight, but require enough profile data
    // to personalize DB-backed chat, mood, and profile views.
    !user?.name ||
    user.name === "CalmChat User" ||
    !user?.phone ||
    !user?.region_dialect;

  if (loadingUser) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centerState}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.centerText}>Preparing CalmChat...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (userError) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centerState}>
          <Text style={styles.centerTitle}>Setup failed</Text>
          <Text style={styles.centerText}>{userError}</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (needsProfileSetup) {
    return (
      <OnboardingScreen
        user={user}
        onComplete={(updatedUser) => setUser(updatedUser)}
      />
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.screenArea}>
        <ActiveScreen
          onNavigate={setActiveTab}
          user={user}
          onUserChange={setUser}
        />
      </View>

      <View style={styles.tabBar}>
        {TABS.map((tab) => {
          const isActive = tab.key === activeTab;

          return (
            <Pressable
              key={tab.key}
              style={styles.tabItem}
              onPress={() => setActiveTab(tab.key)}
            >
              <Text style={[styles.tabIcon, isActive && styles.tabIconActive]}>
                {tab.icon}
              </Text>
              <Text style={[styles.tabLabel, isActive && styles.tabLabelActive]}>
                {tab.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  screenArea: { flex: 1 },
  centerState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  centerTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.foreground,
    marginBottom: 8,
  },
  centerText: {
    color: colors.mutedForeground,
    fontSize: 16,
    marginTop: 12,
    textAlign: "center",
  },
  tabBar: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.card,
    paddingTop: 8,
    paddingBottom: 10,
  },
  tabItem: { flex: 1, alignItems: "center", gap: 2 },
  tabIcon: { fontSize: 22, opacity: 0.5 },
  tabIconActive: { opacity: 1 },
  tabLabel: { fontSize: 12, fontWeight: "600", color: colors.mutedForeground },
  tabLabelActive: { color: colors.primary },
});
