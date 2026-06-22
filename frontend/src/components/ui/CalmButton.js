import React from "react";
import { Pressable, Text, StyleSheet } from "react-native";
import { colors, radius, shadow } from "../../theme/theme";

/**
 * CalmChat의 .calm-btn / .calm-btn-primary / .calm-btn-accent / .calm-btn-ghost 를
 * RN 버튼으로 옮긴 컴포넌트. pill 모양 + 부드러운 그림자.
 */
export function CalmButton({ title, icon, onPress, variant = "primary", disabled = false, style }) {
  const textColor =
    variant === "ghost" ? colors.foreground : variant === "accent" ? colors.accentForeground : colors.primaryForeground;

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.base,
        styles[variant] || styles.primary,
        pressed && styles.pressed,
        disabled && styles.disabled,
        style,
      ]}
    >
      {icon}
      <Text style={[styles.text, { color: textColor }]}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 56,
    borderRadius: radius.pill,
    paddingHorizontal: 24,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  pressed: { transform: [{ scale: 0.98 }] },
  disabled: { opacity: 0.5 },
  primary: { backgroundColor: colors.primary, ...shadow.soft },
  accent: { backgroundColor: colors.accent, ...shadow.soft },
  ghost: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  text: { fontSize: 18, fontWeight: "600" },
});
