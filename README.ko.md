# CUE — Computer Use Engine

[English](README.md) | **한국어**

AI Computer Use 에이전트 프레임워크. Claude Desktop/Code에서 MCP 서버로 연결하여 데스크톱을 자동 제어합니다.

## 아키텍처

```
Claude Desktop/Code (AI 두뇌, Max 구독)
    ↕ MCP protocol (stdio)
CUE MCP Server (Python)
    ↕ pyautogui / pygetwindow / pywin32
Windows Desktop
```

기존의 AI Computer Use 방식은 Claude API를 직접 호출하여 별도 비용이 발생하지만, CUE는 **MCP 서버 아키텍처**를 채택하여 Claude Max 구독만으로 동작합니다.

## 설치

```bash
git clone https://github.com/yonghwan1106/computer-use-engine.git
cd computer-use-engine
pip install -e ".[dev]"
```

## MCP 도구 (12개)

### 스크린샷

| 도구 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `cue_screenshot` | 전체/영역 스크린샷 캡처 | `region_x`, `region_y`, `region_width`, `region_height` |
| `cue_screen_size` | 화면 해상도 반환 | — |
| `cue_cursor_position` | 현재 마우스 커서 좌표 | — |

### 마우스

| 도구 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `cue_click` | 마우스 클릭 | `x`, `y`, `button` (left/right/middle), `clicks` (1~3) |
| `cue_scroll` | 스크롤 | `x`, `y`, `clicks` (양수=위, 음수=아래) |
| `cue_move` | 마우스 이동 | `x`, `y` |
| `cue_drag` | 드래그 | `start_x`, `start_y`, `end_x`, `end_y`, `button` |

### 키보드

| 도구 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `cue_type` | 텍스트 입력 | `text` (한글은 클립보드 자동 fallback) |
| `cue_key` | 키/단축키 입력 | `key` (예: `"enter"`, `"ctrl+c"`, `"alt+tab"`) |

### 윈도우 관리

| 도구 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `cue_list_windows` | 열린 창 목록 조회 | — |
| `cue_focus_window` | 창 포커스 (제목 부분 매칭) | `title` |
| `cue_window_info` | 현재 활성 창 정보 | — |

## Claude Desktop/Code 등록

자동 등록:

```bash
python scripts/register.py
```

수동 등록:

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

등록 후 Claude Desktop/Code를 재시작하세요.

## 사용 예시

등록 완료 후 Claude에게 자연어로 요청하면 됩니다:

- "스크린샷 찍어줘"
- "메모장을 열고 'Hello CUE'를 입력해줘"
- "지금 열려있는 창 목록을 보여줘"
- "Chrome 창으로 전환해줘"
- "화면 중앙을 더블클릭해줘"

## 안전 기능

| 기능 | 설명 |
|------|------|
| 액션 제한 | 세션당 최대 100회 (설정 변경 가능) |
| 앱 차단 | Registry Editor, Windows Security 등 위험 앱 차단 |
| 키 차단 | `win+r`, `ctrl+alt+del` 등 위험 단축키 차단 |
| 감사 로그 | 모든 액션을 JSON Lines 형식으로 기록 |
| FAILSAFE | 마우스를 (0,0)으로 이동하면 즉시 중단 |

설정 파일: `config/default.yaml`

## 프로젝트 구조

```
computer-use-engine/
├── cue/
│   ├── server.py              # FastMCP 서버 + 초기화
│   ├── tools/
│   │   ├── screenshot.py      # 스크린샷 도구 (3개)
│   │   ├── mouse.py           # 마우스 도구 (4개)
│   │   ├── keyboard.py        # 키보드 도구 (2개)
│   │   └── window.py          # 윈도우 도구 (3개)
│   ├── safety/
│   │   ├── guardrails.py      # 안전 검사
│   │   └── logger.py          # 감사 로그
│   └── utils/
│       ├── screen.py          # DPI, 이미지 처리
│       └── keymap.py          # 키 매핑
├── config/default.yaml        # 안전 설정
├── scripts/register.py        # 자동 등록
└── tests/                     # 단위 테스트 (41개)
```

## 테스트

```bash
pytest tests/ -v
```

## 라이선스

Apache 2.0
