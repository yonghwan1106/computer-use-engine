# CUE — Computer Use Engine

AI Computer Use 에이전트 프레임워크. Claude Desktop/Code에서 MCP 서버로 연결하여 데스크톱을 자동 제어합니다.

```
Claude Desktop/Code (AI 두뇌)
    ↕ MCP protocol (stdio)
CUE MCP Server (Python)
    ↕ pyautogui / pygetwindow / pywin32
Windows Desktop
```

## 설치

```bash
cd computer-use-engine
pip install -e ".[dev]"
```

## MCP 도구 (12개)

| 도구 | 설명 |
|------|------|
| `cue_screenshot` | 전체/영역 스크린샷 (JPEG Image 반환) |
| `cue_screen_size` | 화면 해상도 반환 |
| `cue_cursor_position` | 현재 커서 좌표 |
| `cue_click` | 마우스 클릭 (left/right/middle, 1~3회) |
| `cue_scroll` | 스크롤 (양수=위, 음수=아래) |
| `cue_move` | 마우스 이동 |
| `cue_drag` | 드래그 (시작→끝 좌표) |
| `cue_type` | 텍스트 입력 (한글 클립보드 자동 fallback) |
| `cue_key` | 키/단축키 ("ctrl+c", "enter" 등) |
| `cue_list_windows` | 열린 창 목록 |
| `cue_focus_window` | 창 포커스 (제목 부분 매칭) |
| `cue_window_info` | 활성 창 정보 |

## Claude Desktop/Code 등록

```bash
python scripts/register.py
```

또는 수동으로 설정:

**Claude Desktop** (`%APPDATA%/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "cue": {
      "command": "python",
      "args": ["-m", "cue"]
    }
  }
}
```

**Claude Code** (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "cue": {
      "command": "python",
      "args": ["-m", "cue"]
    }
  }
}
```

## 안전 기능

- 세션당 액션 수 제한 (기본 100)
- 앱 허용/차단 목록
- 위험 키 조합 차단 (win+r, ctrl+alt+del)
- JSON Lines 감사 로그
- pyautogui FAILSAFE (마우스를 0,0으로 이동하면 중단)

설정: `config/default.yaml`

## 테스트

```bash
pytest tests/
```

## 라이선스

Apache 2.0
