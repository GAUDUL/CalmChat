import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet, SafeAreaView } from "react-native";
import { colors } from "./src/theme/theme";
import HomeScreen from "./src/screens/HomeScreen";
import ChatScreen from "./src/screens/ChatScreen";
import MoodScreen from "./src/screens/MoodScreen";
import ProfileScreen from "./src/screens/ProfileScreen";

/**
 * react-navigation 없이 useState로 직접 만든 하단 탭바.
 * (CalmChat의 MobileShell 하단 탭과 같은 구성: Home/Chat/Mood/Profile)
 */
const TABS = [
  { key: "Home", label: "홈", icon: "🏠", Component: HomeScreen },
  { key: "Chat", label: "대화", icon: "💬", Component: ChatScreen },
  { key: "Mood", label: "기분", icon: "🙂", Component: MoodScreen },
  { key: "Profile", label: "프로필", icon: "👤", Component: ProfileScreen },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("Home");
  const ActiveScreen =
  TABS.find((t) => t.key === activeTab)?.Component || HomeScreen;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.screenArea}>
        <ActiveScreen onNavigate={setActiveTab} />
      </View>

      <View style={styles.tabBar}>
        {TABS.map((tab) => {
          const isActive = tab.key === activeTab;
          return (
            <Pressable key={tab.key} style={styles.tabItem} onPress={() => setActiveTab(tab.key)}>
              <Text style={[styles.tabIcon, isActive && styles.tabIconActive]}>{tab.icon}</Text>
              <Text style={[styles.tabLabel, isActive && styles.tabLabelActive]}>{tab.label}</Text>
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
