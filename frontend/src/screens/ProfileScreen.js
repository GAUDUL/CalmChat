import React, { useState } from "react";
import { View, Text, Switch, StyleSheet, SafeAreaView, ScrollView } from "react-native";
import { CalmCard } from "../components/ui/CalmCard";
import { colors } from "../theme/theme";

export default function ProfileScreen() {
  const [familyVoiceEnabled, setFamilyVoiceEnabled] = useState(false);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>내 정보</Text>

        <CalmCard style={styles.card}>
          <Text style={styles.label}>이름</Text>
          <Text style={styles.value}>ㅇㅇㅇ</Text>
        </CalmCard>

        <CalmCard style={[styles.card, styles.row]}>
          <View style={styles.rowText}>
            <Text style={styles.label}>가족 목소리로 듣기</Text>
            <Text style={styles.helper}>켜면 등록된 가족 목소리로 답해드려요</Text>
          </View>
          <Switch
            value={familyVoiceEnabled}
            onValueChange={setFamilyVoiceEnabled}
            trackColor={{ true: colors.primary, false: colors.border }}
          />
          {/* TODO: 가족 목소리 등록/토글 API 연동 (현재 백엔드에 라우터 없음 - 필요시 추가) */}
        </CalmCard>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  container: { padding: 20, gap: 14, paddingBottom: 40 },
  title: { fontSize: 22, fontWeight: "700", color: colors.foreground, marginBottom: 8, textAlign: "center" },
  card: { width: "100%" },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  rowText: { flexShrink: 1 },
  label: { fontSize: 17, fontWeight: "600", color: colors.foreground },
  value: { fontSize: 18, color: colors.foreground, marginTop: 4 },
  helper: { fontSize: 13, color: colors.mutedForeground, marginTop: 2, maxWidth: 220 },
});
