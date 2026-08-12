# 25차 세션 기록 — 플러그인 전환 P2: Claude Code 채널 개통 (2026-08-12)

- 문서 목적: 25차 세션의 작업 내용·산출물·다음 시작 포인트 기록
- 범위: TASK-2026-08-12-main-015 (P2 — 어댑터 + marketplace + 자기 적용)
- 상태: done
- 최종 수정일: 2026-08-12
- 관련 문서: [전환 계획 §3-P2](../../../../docs/planning/plugin-transition-plan-2026-08.md), [24차 세션 기록](./plugin_payload_renderer_2026-08-12.md)

## 1. 지시

사용자: "자 다음 가보자" — P1 완료 직후 P2 착수.

## 2. 이 세션의 핵심: `claude plugin` CLI 로 실측했다

P1 은 스펙을 원문으로 확인하지 못한 채 계약을 고정했다. 이 세션에서 호스트에
`claude plugin` CLI 가 있다는 것을 발견해 **추측을 실측으로 바꿨다**:
`validate --strict` (미지 필드·경로 검증), `details` (컴포넌트 인벤토리),
`--plugin-dir` (세션 한정 로드), `marketplace add` / `install`.

**계획이 실측에 두 번 고쳐졌다.**

### (1) 어댑터를 하위 디렉터리에 둘 수 없다

계획 레이아웃은 `plugin/adapters/claude-code/.claude-plugin/plugin.json` 이
payload 를 `../../skills` 로 참조하는 형태였다. validate 가 거부한다:
*"Path contains '..' which could be a path traversal attempt"*.

그래서 **플러그인 루트 = payload 루트**로 두었다. 그러자 Claude Code 의 관례
경로(`skills/`)가 payload 배치와 그대로 겹쳐서, 어댑터가 manifest + hooks
**두 장**으로 줄었다 — 계획이 기대한 "얇은 어댑터" 보다 더 얇아졌다.

### (2) validate 통과는 로드 증명이 아니다

manifest 에 `"mcpServers": "./mcp.json"` 을 선언하면 `validate --strict` 는
**통과한다**. 그런데 `details` 의 인벤토리는 **`MCP servers (0)`** 이었다.
관례 경로 `.mcp.json` 으로 옮기자 `MCP servers (1)`.

검증기는 경로 존재만 보고, 로더는 그 필드를 그렇게 쓰지 않는다. **validate 만
믿었으면 "MCP 등록됨" 이라고 잘못 보고할 뻔했다.** 이 저장소가 반복해서 만난
"선언과 실제가 다르다" 계열의 또 하나이고, 그래서 검사 case 8 이 그 형태의
재발을 코드로 막는다 (manifest 에 `mcpServers` 경로 필드가 있으면 FAIL).

## 3. 산출물

- `plugin/.claude-plugin/plugin.json` — 어댑터 manifest (name/version/description/author/hooks)
- `plugin/adapters/claude-code/hooks.json` — SessionStart 안내 / SessionEnd → §11.1 재생성 명령
- `plugin/.mcp.json` — payload `mcp.json` 과 **같은 렌더러 출력의 두 번째 이름**
- `.claude-plugin/marketplace.json` (저장소 루트) — 이 저장소가 곧 marketplace
- 렌더러 확장: `render_claude_code_manifest` / `render_claude_code_hooks` /
  `render_marketplace_manifest` / `render_repo_plugin_files` (payload + marketplace 를
  저장소 루트 기준으로 합쳐 재생성·drift 판정)
- 검사 7 → **9 case** (어댑터 계약 + marketplace 동기)

## 4. 실측 기록

| 항목 | 결과 |
|---|---|
| `validate --strict plugin` / `validate --strict .` | ✔ / ✔ |
| `--plugin-dir plugin ... details` | Skills 3 / Hooks 2 / MCP servers 1 |
| always-on 토큰 비용 | ~92 tok (호출 시 270~350) |
| `wk` 부재 graceful | 두 hook 모두 안내 + exit 0 (조용한 실패 없음) |
| `marketplace add ./` | ✔ user settings 선언 (`.` 은 거부 — `./` 또는 절대 경로) |
| `install standard-ai-workflow@standard-ai-workflow` | ✔ scope user, enabled, 인벤토리 3/2/1 동일 |

전량 2축 **252/252 ×2 green**, 신설 검사 9/9.

## 5. 다음 시작 포인트

**스킬 네임스페이스 호출과 MCP 승인 UX 는 다음 세션에서 확인된다** — 설치는 현재
세션에 소급 적용되지 않는다. 다음 세션 시작 시 `/standard-ai-workflow:session-start`
가 뜨는지, MCP 서버 승인이 어떻게 뜨는지 **먼저 확인하고 계획 §3-P2 실측 표에 추가**한다.

그 다음 축은 **TASK-016 (P3 멀티 하네스 어댑터)** 또는 **TASK-017 (P4 릴리스
파이프라인 통합)**. P4 는 `plugin/` 이 아직 bump 자동 동기 밖이라는 §7 리스크를 닫는다.

## 6. 남은 리스크

- 스킬/MCP 의 **런타임 동작**은 미확인 (설치·인벤토리까지만 실측). 위 §5.
- hook 명령이 POSIX sh 전제다 (`command -v`). Windows 하네스에서의 동작은 미확인 —
  os-matrix 축에 플러그인 셀은 아직 없다.
- `plugin/` 은 릴리스 파이프라인 밖 (P4 전까지 bump 후 `--apply` 수동 재생성 필요).
- 이 저장소의 Claude Code 설정에 플러그인이 **user scope 로 설치돼 있다** (사용자
  승인 후 진행). 되돌리려면 `claude plugin uninstall` + `marketplace remove`.
