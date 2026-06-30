import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { colors } from "./src/theme/theme";
import ChatScreen from "./src/screens/ChatScreen";
import HomeScreen from "./src/screens/HomeScreen";
import MoodScreen from "./src/screens/MoodScreen";
import OnboardingScreen from "./src/screens/OnboardingScreen";
import ProfileScreen from "./src/screens/ProfileScreen";
import { fetchMetrics, registerDeviceUser } from "./src/api/client";
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
  const [metrics, setMetrics] = useState(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState(null);

  const refreshMetrics = useCallback(
    async ({ retries = 0, delayMs = 500 } = {}) => {
      if (!user?.id) {
        return null;
      }

      setMetricsLoading(true);
      setMetricsError(null);

      let lastError = null;

      for (let attempt = 0; attempt <= retries; attempt += 1) {
        if (attempt > 0) {
          await new Promise((resolve) => setTimeout(resolve, delayMs));
        }

        try {
          const nextMetrics = await fetchMetrics(user.id);
          setMetrics(nextMetrics);
          setMetricsLoading(false);
          return nextMetrics;
        } catch (err) {
          lastError = err;
        }
      }

      console.error("Failed to load metrics:", lastError);
      setMetricsError("Could not load your mood data.");
      setMetricsLoading(false);
      return null;
    },
    [user?.id]
  );

  useEffect(() => {
    let mounted = true;

    async function initializeUser() {
      try {
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

  useEffect(() => {
    refreshMetrics();
  }, [refreshMetrics]);

  const ActiveScreen =
    TABS.find((tab) => tab.key === activeTab)?.Component || HomeScreen;
  const needsProfileSetup =
    !user?.onboarding_completed ||
    !user?.name ||
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
          metrics={metrics}
          metricsLoading={metricsLoading}
          metricsError={metricsError}
          onRefreshMetrics={refreshMetrics}
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
  tabIcon: { fontSize: 18, fontWeight: "800", opacity: 0.5 },
  tabIconActive: { opacity: 1 },
  tabLabel: { fontSize: 12, fontWeight: "600", color: colors.mutedForeground },
  tabLabelActive: { color: colors.primary },
});
