import React, { useEffect, useRef } from "react";
import { Animated, Image, View, Text, StyleSheet } from "react-native";
import { colors, shadow } from "../../theme/theme";

/**
 * CalmChat의 AnimatedAvatar(단일 이미지 + CSS 애니메이션)를 RN으로 옮긴 버전.
 *
 * - imageUri를 안 주면(=아바타 디자인 미정 상태) 동그란 placeholder + 이모지로 표시.
 *   나중에 실제 아바타 이미지/캐릭터가 정해지면 imageUri만 넘기면 됨 (로직 변경 불필요).
 * - state: "idle" | "listening" | "thinking" | "speaking"
 *   idle=breathe(숨쉬기), listening=tilt(좌우 기울임)+glow ring,
 *   thinking=float(위아래 떠다님)+점 3개, speaking=bob(작게 들썩임)
 */
export function AnimatedAvatar({ imageUri, state = "idle", size = 140 }) {
  const scale = useRef(new Animated.Value(1)).current;
  const translateY = useRef(new Animated.Value(0)).current;
  const rotate = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    scale.setValue(1);
    translateY.setValue(0);
    rotate.setValue(0);

    let loop;
    if (state === "listening") {
      loop = Animated.loop(
        Animated.sequence([
          Animated.timing(rotate, { toValue: 1, duration: 1200, useNativeDriver: true }),
          Animated.timing(rotate, { toValue: -1, duration: 1200, useNativeDriver: true }),
        ])
      );
    } else if (state === "thinking") {
      loop = Animated.loop(
        Animated.sequence([
          Animated.timing(translateY, { toValue: -6, duration: 1000, useNativeDriver: true }),
          Animated.timing(translateY, { toValue: 0, duration: 1000, useNativeDriver: true }),
        ])
      );
    } else if (state === "speaking") {
      loop = Animated.loop(
        Animated.sequence([
          Animated.timing(scale, { toValue: 1.02, duration: 250, useNativeDriver: true }),
          Animated.timing(scale, { toValue: 1, duration: 250, useNativeDriver: true }),
        ])
      );
    } else {
      // idle - breathe
      loop = Animated.loop(
        Animated.sequence([
          Animated.timing(scale, { toValue: 1.035, duration: 1800, useNativeDriver: true }),
          Animated.timing(scale, { toValue: 1, duration: 1800, useNativeDriver: true }),
        ])
      );
    }
    loop.start();
    return () => loop.stop();
  }, [state]);

  const rotateDeg = rotate.interpolate({ inputRange: [-1, 1], outputRange: ["-4deg", "4deg"] });

  return (
    <View style={[styles.wrapper, { width: size + 24, height: size + 24 }]}>
      <Animated.View
        style={[
          styles.circle,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            transform: [{ scale }, { translateY }, { rotate: rotateDeg }],
          },
          shadow.soft,
        ]}
      >
        {imageUri ? (
          <Image source={{ uri: imageUri }} style={styles.image} resizeMode="cover" />
        ) : (
          // TODO: 아바타 디자인 확정되면 여기를 실제 캐릭터/이미지로 교체
          <View style={styles.placeholder}>
            <Text style={{ fontSize: size * 0.4 }}>🙂</Text>
          </View>
        )}
      </Animated.View>

      {state === "listening" && (
        <View
          pointerEvents="none"
          style={[styles.glowRing, { width: size + 16, height: size + 16, borderRadius: (size + 16) / 2 }]}
        />
      )}

      {state === "thinking" && (
        <View style={styles.dots} pointerEvents="none">
          <View style={styles.dot} />
          <View style={[styles.dot, { opacity: 0.6 }]} />
          <View style={[styles.dot, { opacity: 0.3 }]} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { alignItems: "center", justifyContent: "center" },
  circle: {
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.secondary,
  },
  image: { width: "100%", height: "100%" },
  placeholder: {
    width: "100%",
    height: "100%",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.secondary,
  },
  glowRing: {
    position: "absolute",
    borderWidth: 3,
    borderColor: colors.primary,
    opacity: 0.5,
  },
  dots: { position: "absolute", bottom: -2, flexDirection: "row", gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.primary },
});
