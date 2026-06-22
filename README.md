# 노인 정서 동반자 AI 앱

실제 모델/엔진이 아직 미결정인 부분은 인터페이스만 잡아두고 `TODO`로 표시했습니다.

## 사전 요구 환경

### 공통 환경

| 항목 | 버전 |
|------|------|
| Python | 3.10+ |
| Node.js | 20.19.x ~ 22.x |
| npm | 9 ~ 10 |
| MySQL | 8.x |
| ffmpeg | 최신 |

---

### Android / React Native 환경

| 항목 | 요구사항 |
|------|----------|
| Java | 17 |
| Android Studio | 최신 Stable |
| Android SDK | API 34+ |
| Emulator | Pixel 권장 |

---

## 🔐 Android 권한

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```