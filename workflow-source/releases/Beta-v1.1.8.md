# Beta v1.1.8 (2026-08-12)

> **상태: 릴리스 준비.** `tool_version = v1.1.8-beta`, tag `v1.1.8-beta`.
> **patch release** — 16~19차 세션 묶음: **MCP bundle 분리** (read-only / write) +
> **CLI cross-platform** (os-matrix CI, Windows 첫 실측) + **네임스페이스 격상 2단계
> 완결** (tools·bootstrap_lib → `workflow_kit.*`, PyPI 이동 단계 종료) + 안전망 2건
> (status 보존 / no_repo_write 실행-중 감시). `cmd_release` 경로의 **5번째 실전 발행**.
>
> **본 릴리스가 2nd deprecation cycle 의 시계를 시작한다** — 구경로 shim (tools /
> bootstrap_lib) 과 `--bundle` 기본값 `all` 은 다음 릴리스에서 drop 예정.
>
> PyPI 배포는 정책상 미실행 (릴리스 채널 = GitHub Releases).

## 0. 릴리스 판정

본 릴리스의 공통 주제는 **"표면을 정직하게, 이름 충돌 없이"** 다.

- **bundle 분리** — "read_only" 라는 이름 안에 write 도구가 살던 긴장을 서버
  선택자·렌더러 기본값·검사 3층으로 정리했다. 분리는 서버 능력만으로는 장식이다.
- **Windows 는 로컬에 없던 축** — darwin `/private` 4건과 같은 계열. os-matrix CI
  가 그 축을 상설화했고, 첫 실측에서 소비자 표면 8 probe 전부 PASS.
- **일반명 top-level 은 배포의 blocker** — `tools`/`bootstrap_lib` 를
  `workflow_kit.*` 로 격상 (구경로 shim 1 cycle 유지). 이관 중 "shim 경유
  monkeypatch 는 impl 에 안 먹힌다" 는 사고 1건을 실측·복원했다 — source-bound
  소비자는 impl 을 직표적한다.

## 1. 릴리스 요약

- 범위: `v1.1.7-beta..HEAD` (TASK-2026-08-12-main-003~009, 8+ commit)
- MCP bundle 분리: `--bundle read-only(11)/write(2)/all(13)` + 렌더러 정직한 기본 + 검사 삼자 강제
- CLI 배포 검토 (uv/pipx 권장 경로 문서화) + cross-platform (os-matrix CI: Windows·macOS probe 8/8)
- 네임스페이스 격상 2단계 완결: `workflow_kit.tools` (43) + `workflow_kit.bootstrap_lib` (9) + 구경로 shim
- backlog-update `--status` 미지정 = 기존 상태 보존 / `check_no_repo_write` 실행-중 폴링
- 전량 검사 **251/251 PASS** ×2축 (격리 venv, `--tmp-dir` 실디스크) + os-matrix (windows/macos)

## 2. deliverable

### 2.1 MCP bundle 분리 (TASK-003, `bd121f5`)

- registry bundle 선택자 — read-only 11 / write 2 (`workflow_write_bundle`) /
  all 13 (1st cycle 기본 + deprecation 경고). bundle 밖 tools/call 거부.
- bootstrap emit: 기존 alias 전부 `--bundle read-only`, claude-code·MiniMax 는
  `standardAiWorkflowWrite` entry 동시 emit (MiniMax write = `manual_review_only`),
  mavis 글로벌은 read-only 만. 자기 적용: 저장소 `.mcp.json` 2-server 분리.
- `check_read_only_mcp_server`: RO∪W==all + 교집합 0 + RO 서버의 write 호출 거부.
  ADR-003 v1.1.8 절 신설.

### 2.2 CLI 배포 검토 + cross-platform (TASK-004·005, `bd121f5`·`9351e17`)

- 검토 (docs/planning/cli-distribution-review-2026-08.md): wheel top-level 실측 →
  PyPI 는 네임스페이스 격상 선행 (→ §2.3). 권고 단기안 (uv/pipx + GH Release
  wheel 격리 설치) 을 INSTALLATION §3 에 반영.
- `os-matrix.yml`: windows-latest + macos-latest 에서 소비자 경로 설치 + 8-probe
  (wk 핵심 명령 + MCP 브리지). **Windows 첫 실측 8/8 PASS.** 유일한 top-level
  POSIX 의존 (`profiling.py` 의 `import resource`) 가드. 지원 tier 문서화.

### 2.3 네임스페이스 격상 2단계 완결 (TASK-006·007, `74889f3`·`bcd2c7d`)

- `tools` 43모듈 → `workflow_kit.tools`, `bootstrap_lib` 9모듈 →
  `workflow_kit.bootstrap_lib`. 구경로는 vars-copy shim (import·path-load·직접
  실행·`python -m` 전부 호환), 자산 (hooks/completions) 은 원위치.
- entry points 36 + TOOL_MODULES 36 재표적, 테스트 ~84파일 재표적, mypy 는
  overrides 로 격상 유예 (crawl 137→191파일 0 오류).
- 사고 1건 (복원 완료, HEAD 무손상): shim 경유 monkeypatch 미적용으로 version-bump
  계열 검사가 실저장소 pyproject 를 오염 — source-bound 소비자를 impl 직표적으로
  전환해 해소.

### 2.4 안전망 2건 (TASK-008·009, `5b89813`)

- backlog-update `--status` 미지정 = **기존 상태 보존** (미지정은 "바꾸지 말라").
  done 강등은 명시 요청에만. layout 검사 8→9 case.
- `check_no_repo_write` 실행-중 porcelain 폴링 — "건드렸다 되돌리면 통과" 하던
  계약 한계 해소 (§6 리스크). 미지 transient = FAIL, 알려진 touch-and-restore 는
  단방향 원장 (폴링의 음성은 증명이 아님을 명시). 실측: 감시 13개 전부 무접촉.

### 2.5 federation self-host + v1.1.7 발행 후속 (TASK-2026-08-12-main-001·002)

v1.1.7-beta 범위 직후 같은 날 작업: plex 상시 serving (`--print-systemd-unit`) 과
v1.1.7-beta 발행 자체는 [Beta-v1.1.7.md](./Beta-v1.1.7.md) 참조 — 본 노트 범위는
그 이후 커밋이다.

## 3. smoke 회귀

누적 smoke test **251/251 PASS** (2026-08-12, `dev,release,mcp-sdk` extra 를 깐
격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신 전량
결과* 를 반영하는 살아있는 지표다.

신규 smoke 파일 없음 (251 유지). 기존 검사 case 확장:

- `check_backlog_update_layout` 8→**9** (status 보존 되주입)
- `check_no_repo_write` 1→**2** (실행-중 폴링 되주입)
- `check_registry_server` 10→**11** (systemd unit 계약; v1.1.7 범위의 후속 반영)
- `check_read_only_mcp_server` (bundle 삼자 강제) · `check_mcp_tool_descriptors`
  case 7 bundle-aware · `check_standard_single_source` 9 case 유지
- 신규 CI 축: `os-matrix.yml` (windows/macos CLI probe — smoke 파일 수 밖의 축)

## 4. 1차 출처 (cross-ref)

- [TASK-2026-08-12-main-003](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-12-main-003.md) ~ [TASK-2026-08-12-main-009](../../ai-workflow/memory/active/main/backlog/tasks/TASK-2026-08-12-main-009.md)
- 세션 기록: `ai-workflow/memory/active/main/sessions/` 16차~19차
- [ADR-003 v1.1.8 절](../../docs/architecture/ADR-003-read-only-mcp-default-policy.md) · [배포 검토](../../docs/planning/cli-distribution-review-2026-08.md)
- 이전 release note: [Beta-v1.1.7.md](./Beta-v1.1.7.md)

## 5. 후속

- **2nd cycle 묶음 (다음 릴리스)**: tools/bootstrap_lib shim drop + `--bundle`
  기본값 `all`→`read-only` — 그 후 wheel top-level 이 `workflow_kit` 하나가 되어
  PyPI 발행은 소유자 결정만 남는다.
- cross-host federation — 두 번째 호스트 = MacBook 확정 (시점 추후).
- stdio-sdk bundle 지원 (승격 기준과 함께).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-12T08:07:57Z)_

- total wiki pages: **93**
- total memory entries: **9**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
