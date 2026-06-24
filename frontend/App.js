import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet, SafeAreaView } from "react-native";
import { colors } from "./src/theme/theme";
import HomeScreen from "./src/screens/HomeScreen";
import ChatScreen from "./src/screens/ChatScreen";
import MoodScreen from "./src/screens/MoodScreen";
import ProfileScreen from "./src/screens/ProfileScreen";

const TABS = [
  { key: "Home", label: "Home", icon: "🏠", Component: HomeScreen },
  { key: "Chat", label: "Chat", icon: "💬", Component: ChatScreen },
  { key: "Mood", label: "Mood", icon: "🙂", Component: MoodScreen },
  { key: "Profile", label: "Profile", icon: "👤", Component: ProfileScreen },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("Home");
  const ActiveScreen =
    TABS.find((tab) => tab.key === activeTab)?.Component || HomeScreen;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.screenArea}>
        <ActiveScreen onNavigate={setActiveTab} />
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
