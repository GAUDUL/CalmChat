import React from "react";
import { View, StyleSheet } from "react-native";
import { colors, radius, shadow } from "../../theme/theme";

/** CalmChat의 .calm-card 를 옮긴 카드. warm=true면 surface-warm 배경 사용 */
export function CalmCard({ children, warm = false, style }) {
  return <View style={[styles.card, warm && styles.warm, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.xxl,
    padding: 20,
    ...shadow.card,
  },
  warm: {
    backgroundColor: colors.surfaceWarm,
  },
});
