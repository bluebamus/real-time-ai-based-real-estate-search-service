# real-time-ai-based-real-estate-search-service
Real-time AI-based real estate search service

# gemini cli model setting
명령행 플래그로 지정

    bash/zsh: gemini --model gemini-2.5-flash 또는 gemini -m gemini-2.5-flash 형태로 실행한다.

환경변수로 고정

    Linux/macOS: export GEMINI_MODEL="gemini-2.5-flash" 후 gemini 실행하면 해당 모델이 기본 적용된다.

Windows PowerShell: $env:GEMINI_MODEL="gemini-2.5-flash"; gemini 처럼 설정 후 실행한다.
영구 설정 팁

    셸 프로파일에 추가

        예: ~/.bashrc, ~/.zshrc 등에 export GEMINI_MODEL="gemini-2.5-flash"를 추가하면 매번 플래시로 시작한다.