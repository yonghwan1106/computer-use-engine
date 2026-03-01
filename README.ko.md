# CUE — Computer Use Enforcer

[English](README.md) | **한국어**

> **AI 에이전트와 데스크톱 사이의 안전 계층.**

CUE는 AI Computer Use 에이전트를 위한 안전 미들웨어입니다. 정책 기반 모니터링, 가드레일, 감사 로그를 제공하여 AI 에이전트가 데스크톱을 안전하고 규정에 맞게 제어할 수 있도록 합니다.

---

## 왜 필요한가

AI Computer Use가 빠르게 확산되고 있지만, 안전 인프라는 따라가지 못하고 있습니다:

- **급속한 도입** — 2026년 말까지 기업 40%가 AI Computer Use 에이전트 도입 예정
- **가드레일 부재** — 자율 에이전트에 안전 제어를 갖춘 조직은 50%에 불과
- **규제 시행** — EU AI Act (2026.08) 고위험 AI 시스템에 인간 감독 의무화

AI 에이전트와 데스크톱 사이에서 안전 정책을 집행하는 오픈소스 프레임워크가 없습니다. CUE가 그 빈자리를 채웁니다.

## CUE가 하는 일

```
┌─────────────────────────────────┐
│  AI 에이전트 (Claude, GPT 등)    │
└──────────┬──────────────────────┘
           │ MCP 프로토콜 (stdio)
┌──────────▼──────────────────────┐
│  CUE — Computer Use Enforcer   │  ← 이 프로젝트
│  ┌────────────────────────────┐ │
│  │ 정책 엔진                   │ │  위험 분류, 액션 필터링
│  │ 가드레일                    │ │  앱 차단, 키 차단, 속도 제한
│  │ 감사 로거                   │ │  JSONL 컴플라이언스 기록
│  │ 모니터 (개발 예정)           │ │  실시간 대시보드
│  └────────────────────────────┘ │
└──────────┬──────────────────────┘
           │ pyautogui / pygetwindow / pywin32
┌──────────▼──────────────────────┐
│  데스크톱 OS                     │
└─────────────────────────────────┘
```

### 핵심 가치

| 기능 | 상태 | 설명 |
|------|------|------|
| **액션 가드레일** | 제공 중 | 앱 차단, 키 차단, 세션당 액션 제한 |
| **감사 로깅** | 제공 중 | 모든 액션을 JSONL로 기록 |
| **FAILSAFE** | 제공 중 | 마우스를 (0,0)으로 이동 시 즉시 중단 |
| **정책 엔진** | Phase 1 | 위험 분류, 규칙 기반 액션 필터링 |
| **실시간 모니터** | Phase 2 | 이벤트 스트리밍 대시보드 |
| **Human-in-the-Loop** | Phase 3 | 고위험 액션 승인 워크플로우 |
| **에이전트 어댑터** | Phase 4 | 에이전트 무관 백엔드 (Claude, GPT, 오픈소스) |
| **컴플라이언스 리포트** | Phase 5 | EU AI Act, SOC 2 자동 보고서 |

## 빠른 시작

### 1. 설치

```bash
git clone https://github.com/yonghwan1106/computer-use-engine.git
cd computer-use-engine
pip install -e .
```

### 2. Claude 등록

```bash
python scripts/register.py
```

Claude Desktop과 Claude Code에 자동으로 등록됩니다.

### 3. 재시작 후 사용

Claude Desktop/Code를 재시작하고 자연어로 요청하면 됩니다:

- "스크린샷 찍어줘"
- "메모장을 열고 'Hello CUE'를 입력해줘"
- "지금 열려있는 창 목록을 보여줘"
- "Chrome 창으로 전환해줘"

## 현재 기능

### MCP 도구 (12개)

#### 스크린샷

| 도구 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `cue_screenshot` | 전체/영역 스크린샷 캡처 | `region_x`, `region_y`, `region_width`, `region_height` |
| `cue_screen_size` | 화면 해상도 반환 | — |
| `cue_cursor_position` | 현재 마우스 커서 좌표 | — |

#### 마우스

| 도구 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `cue_click` | 마우스 클릭 | `x`, `y`, `button` (left/right/middle), `clicks` (1~3) |
| `cue_scroll` | 스크롤 | `x`, `y`, `clicks` (양수=위, 음수=아래) |
| `cue_move` | 마우스 이동 | `x`, `y` |
| `cue_drag` | 드래그 | `start_x`, `start_y`, `end_x`, `end_y`, `button` |

#### 키보드

| 도구 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `cue_type` | 텍스트 입력 | `text` (한글은 클립보드 자동 fallback) |
| `cue_key` | 키/단축키 입력 | `key` (예: `"enter"`, `"ctrl+c"`, `"alt+tab"`) |

#### 윈도우 관리

| 도구 | 설명 | 주요 파라미터 |
|------|------|--------------|
| `cue_list_windows` | 열린 창 목록 조회 | — |
| `cue_focus_window` | 창 포커스 (제목 부분 매칭) | `title` |
| `cue_window_info` | 현재 활성 창 정보 | — |

### 안전 기능

| 기능 | 설명 | 기본값 |
|------|------|--------|
| **액션 제한** | 세션당 최대 액션 수 | 100 |
| **앱 차단** | 위험 앱과의 상호작용 차단 | Registry Editor, Windows Security |
| **키 차단** | 위험한 단축키 차단 | `win+r`, `ctrl+alt+del` |
| **감사 로그** | 모든 액션을 JSONL로 기록 | `cue_audit.jsonl` |
| **FAILSAFE** | 마우스를 (0,0)으로 이동 시 즉시 중단 | 활성화 |
| **액션 지연** | 안전을 위한 액션 간 대기 | 50ms |

## 안전 정책 설정

`config/default.yaml`에서 모든 안전 설정을 변경할 수 있습니다:

```yaml
safety:
  max_actions_per_session: 100
  action_delay: 0.05
  failsafe: true
  allowed_apps: []
  blocked_apps:
    - "Windows Security"
    - "Registry Editor"
    - "Task Manager"
  blocked_keys:
    - "win+r"
    - "alt+f4"
    - "ctrl+alt+del"
```

## 수동 등록

`register.py` 대신 직접 설정하려면:

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

## 프로젝트 구조

```
computer-use-engine/
├── cue/
│   ├── __init__.py            # 패키지 버전
│   ├── __main__.py            # python -m cue 진입점
│   ├── server.py              # FastMCP 서버 초기화
│   ├── tools/
│   │   ├── screenshot.py      # 스크린샷 도구 (3개)
│   │   ├── mouse.py           # 마우스 도구 (4개)
│   │   ├── keyboard.py        # 키보드 도구 (2개)
│   │   └── window.py          # 윈도우 도구 (3개)
│   ├── safety/
│   │   ├── guardrails.py      # 안전 검사
│   │   └── logger.py          # 감사 로그
│   ├── core/                  # 정책 엔진, 위험 점수 (Phase 1)
│   ├── monitor/               # 실시간 대시보드 (Phase 2)
│   ├── adapters/              # 에이전트 어댑터 (Phase 4)
│   └── utils/
│       ├── screen.py          # DPI, 이미지 처리
│       └── keymap.py          # 키 매핑
├── config/default.yaml        # 안전 설정
├── scripts/register.py        # 자동 등록
└── tests/                     # 단위 테스트
```

## 개발

```bash
# 개발 의존성 포함 설치
pip install -e ".[dev]"

# 테스트 실행
pytest tests/ -v

# 서버 직접 실행 (stdio 모드)
python -m cue
```

## 로드맵

| Phase | 목표 | 상태 |
|-------|------|------|
| **MVP** | MCP 서버, 12개 도구, 기본 가드레일 | 완료 |
| **Phase 1** | 정책 엔진, 위험 분류, 세션 관리 | 다음 |
| **Phase 2** | 실시간 모니터링 대시보드, 이벤트 스트리밍 | 예정 |
| **Phase 3** | Human-in-the-Loop 승인 워크플로우 | 예정 |
| **Phase 4** | 에이전트 무관 어댑터 (Claude, GPT, Agent-S) | 예정 |
| **Phase 5** | 컴플라이언스 리포트 (EU AI Act, SOC 2) | 예정 |

## 요구사항

- Python 3.11+
- Windows 10/11
- MCP 지원 Claude Desktop 또는 Claude Code

## 라이선스

[Apache 2.0](LICENSE)
