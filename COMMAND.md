# 🛠️ Command & Workflow Guide (명령어 및 워크플로우 가이드)

이 문서는 프로젝트에서 사용하는 CLI 도구 설정과 Claude 기반의 작업 절차를 안내합니다.

---

## 🚀 CLI 도구 설정

- `Gemini CLI`와 `Claude CLI`의 주요 설정 방법입니다.

### Gemini CLI 모델 설정

- Gemini CLI에서 특정 모델을 사용하도록 설정하는 방법입니다.

### 명령행 플래그로 지정
- 실행할 때마다 일시적으로 모델을 지정합니다.

```bash
# bash/zsh 환경에서 아래와 같이 실행합니다.
gemini --model gemini-2.5-flash
# 또는 짧은 형태로 실행합니다.
gemini -m gemini-2.5-flash
```


## 환경변수로 고정

- Linux/macOS: export GEMINI_MODEL="gemini-2.5-flash" 후 gemini 실행하면 해당 모델이 기본 적용된다.
- Windows PowerShell: $env:GEMINI_MODEL="gemini-2.5-flash"; gemini 처럼 설정 후 실행한다.

## 영구 설정 팁

### 셸 프로파일에 추가

```
예: ~/.bashrc, ~/.zshrc 등에 export GEMINI_MODEL="gemini-2.5-flash"를 추가하면 매번 플래시로 시작한다.
```

# YOLO 모드 활성화
## 기본 YOLO 모드 활성화
- claude --dangerously-skip-permissions

## claude-yolo 래퍼 사용 (권장)
- npm install -g github:maxparez/claude-yolo

```bash
# YOLO 모드로 전환
claude-yolo mode yolo

# SAFE 모드로 전환 (일반 Claude CLI)
claude-yolo mode safe

# 현재 모드 확인
claude-yolo mode

# YOLO 모드로 실행
claude-yolo --yolo

# SAFE 모드로 실행
claude-yolo --safe
```
