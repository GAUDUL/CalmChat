/**
 * CalmChat 디자인 참고 프로젝트(src/styles.css)의 OKLCH 토큰을
 * React Native StyleSheet에서 쓸 수 있는 값으로 옮긴 테마.
 * (RN은 oklch()를 지원하지 않아 근접한 HEX로 변환 — 원본 주석에 있던
 *  HEX는 그대로 사용, 나머지는 같은 명도/채도 계열로 근사함)
 */

export const colors = {
  background: "#F8F6F2", // cream
  foreground: "#2D2D2D",

  surface: "#FCFBF9",
  surfaceWarm: "#EDE8DE",

  card: "#FCFBF9",
  cardForeground: "#2D2D2D",

  primary: "#6F8F72", // gentle green
  primaryForeground: "#FCFBF9",

  secondary: "#A8B8A1",
  secondaryForeground: "#2D2D2D",

  muted: "#EDEAE3",
  mutedForeground: "#76726A",

  accent: "#D89A6A", // warm orange
  accentForeground: "#FCFBF9",

  destructive: "#C1473A",
  destructiveForeground: "#FCFBF9",

  border: "#DDD8CC",
};

export const radius = {
  sm: 16,
  md: 18,
  lg: 20,
  xl: 24,
  xxl: 28,
  pill: 9999,
};

export const shadow = {
  soft: {
    shadowColor: colors.primary,
    shadowOpacity: 0.18,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  card: {
    shadowColor: "#5B5346",
    shadowOpacity: 0.12,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 3,
  },
};

export const typography = {
  // TODO: CalmChat은 Nunito 폰트 사용 -> expo-font로 로드 후 fontFamily 지정
  fontFamily: undefined,
  base: 18,
  h1: 30,
  h2: 24,
  h3: 20,
  body: 17,
  caption: 14,
};
