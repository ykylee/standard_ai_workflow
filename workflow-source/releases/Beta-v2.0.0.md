# Beta v2.0.0 (2026-11-21) — 2.0 허브 베타

> **상태: 릴리스 준비.** package `2.0.0`, runtime `__version__ = 2.0.0`, tag `v2.0.0` — **2.0 의 첫 판, 베타**
> (계약 보장 전 — 판 번호는 정수, 베타 여부는 이 표기로. 소유자 2026-11-21).
> **major (2.x 줄의 시작)** — 워크플로우의 정본이 각 저장소의 `ai-workflow/` 파일에서 **워크플로우 허브**(서버 하나)로
> 옮겨 간다. 1.x 는 `release/1.x` 에서 2028-07-20 까지 결함 수리만 한다 (같은 날 1.x 안내 판 `v1.30.0`).
>
> 등급 근거 (§1.5 · 소유자 2026-11-20 · 2026-11-21): v1.29.0 이후 커밋 62 — feat 25, fix 5, docs 17, breaking 1.
> **공개 Python API 시그니처 제거 0 · `wk` 진입점 제거 0** — 1.x API 는 2.0 에서도 이어진다 (요구 R0.2).
> 깨지는 것은 **배포 표면 하나**: 이 줄(`main`)은 kit 플러그인 채널(`.claude-plugin/marketplace.json` · 플러그인 zip)을
> 내지 않는다 (`feat(2.0)!`, R16.6). 이 판은 GitHub 'latest' 다 (소유자 2026-11-21).
> 판 번호: 처음엔 PEP 440 `2.0.0b1` 로 올렸으나 키트 16곳(발행 도구 · doctor · 진입점 판 비교 · 문서 판 정규식 ·
> MiniMax manifest 의 SemVer)이 정수 판을 가정해 깨졌다 — 소유자 결정으로 정수 `2.0.0` 에 베타 표기. 2.0 계약(허브 API · MCP 도구 · 생성물)의 보장 기간은 베타를 벗는
> stable 선언 때 정한다 (PURPOSE G3 2.0판).

## 0. 2.0 은 무엇인가

- **허브** = 프로세스 하나 + SQLite 파일 하나 (`python -m workflow_kit hub serve`, `pip install "<wheel>[hub]"`).
  task · handoff · 이력 · 로드맵 · 공유 지침 · 위키 · memory_index 의 **정본**이 허브에 있다. git 은 그 내보내기다.
- **작업 환경은 kit 를 깔지 않는다** — 하네스(Claude Code · Codex · MiniMax Code · Antigravity)가 허브의 원격 MCP
  (`<허브>/mcp`)로 붙는다. 셋업이 쓰는 파일은 `.gitignore` 한 줄 · 진입 파일 렌더 영역 · 하네스 설정 · 토큰 파일
  (`.workflow-hub/env`, git 제외) 뿐이다.
- **사람은 화면으로** — `<허브>/ui/`: 프로젝트 · task · 이력 · 콜사인 표(누가 무엇을) · 지침 제안과 승인 · 위키 · 결정 답.
- 계약 정본 [`core/hub_spec.md`](../core/hub_spec.md), 운영 [`docs/HUB_OPERATIONS.md`](../../docs/HUB_OPERATIONS.md),
  요구와 실측 [`docs/planning/workflow-hub-requirements-2026-11.md`](../../docs/planning/workflow-hub-requirements-2026-11.md).

## 1. 릴리스 요약 (M-031 ~ M-040)

- 범위: `v1.29.0..` **62 commits** (merge 제외) — feat 25 · fix 5 · docs 17 · chore 12 · test 1 · release 2 (발행 준비 포함).
- 누적 smoke **346/346 PASS** (로컬 `--branch-context=all` = 346 × native/slash).
- 검사 파일 수 → 346 (허브 검사 11개 — `check_hub_core` · `bootstrap` · `judge` · `memory` · `wiki` · `client` · `ui` ·
  `migrate` · `marker_1x` · `transfer` · `setup_guide`, 그리고 `check_release_prerelease_latest`).
- 허브: MCP 도구 **55** (토큰 없이 쓰는 부트스트랩 묶음 6 + 토큰 묶음 49), HTTP `POST /v1/tools/<이름>` 은 같은 함수,
  DB 판 **10** (시작 때 이관 · 이관 전 사본).

## 2. 소비자에게 보이는 변화

### 2.1 허브 (M-033 ~ M-037)

- 프로젝트 · 콜사인(사람 / 에이전트, 소유자 승인) · task(계획 · 주장 · 결정 · 진행 · 닫기, 판 충돌 409) · 이력 · handoff ·
  상태(`state.json` 꼴 생성물) · 로드맵 판정 · 공유 지침(진입 파일 렌더 영역, 사람만 판을 올리고 에이전트는 제안) ·
  위키 · memory_index · 체크포인트(compact 중계).
- 결정 답은 **승인된 human 콜사인만**, `responder` = 그 콜사인 — 에이전트가 자기 계획의 결정을 닫지 못한다.
- 선택 클라이언트 `hub_client.py` (표준 라이브러리만, 허브가 `/v1/bootstrap/hub_client.py` 로 내려준다): 오프라인
  보낼편지함 · 브리핑 캐시 · 1.x 전환 운반 · 허브 간 이전 · 부트스트랩.

### 2.2 셋업 — 페이지만 읽고 스스로 (M-039 WBS-39.1)

- 저장소에서 에이전트에게 "`<허브>/setup.md` 를 읽고 이 저장소를 셋업해" — 등록(또는 합류) · `.gitignore` 확인 · 토큰
  파일 · 진입 파일 · 하네스 설정. 하네스의 안전 장치(Claude Code `.mcp.json` 승인 · Codex 샌드박스 · Antigravity 평문
  토큰)는 사람에게 넘긴다. 실측: **4 하네스 모두 빈 폴더에서 페이지만 읽고 셋업 완료** (requirements §16.7).
- git 원격이 없는 저장소는 로컬 키로 등록하고, 원격이 생기면 소유자가 `hub_project_bind_remote` 로 묶는다.

### 2.3 1.x 전환 (M-038)

- `hub_client.py migrate plan` → `migrate import <MIG> all` — task · 보관 · handoff · 로드맵 · 위키 · memory_index ·
  체크포인트 · 지침 초안 · 결정 응답 · PURPOSE/PROFILE. 원본 파일은 지우지 않는다. 이 저장소 실제 들여오기(테스트베드 허브): 1193 파일 실패 0.
- '허브로 옮김' 표식(`ai-workflow/HUB_MIGRATED.json`)을 커밋하면 1.x 쓰기 명령이 거절된다 (1.30.0 이상).

### 2.4 허브 간 프로젝트 이전 (M-039 WBS-39.4)

- 관리자 CLI `hub admin project export --seal-to` / `import`, 또는 소유자가 `hub_client.py move <대상> <초대 코드>`.
  원본은 봉인돼 `410 project_moved` + 새 주소, 콜사인 토큰은 이어진다.

### 2.5 배포 표면 — **깨지는 것** (`feat(2.0)!`, R16.6)

- 이 줄은 kit 플러그인 채널을 내지 않는다: `main` 에 `.claude-plugin/marketplace.json` 이 없고 Release 에 플러그인 zip 이
  없다 (`plugin_payload.KIT_PLUGIN_CHANNEL`). GitHub 원격 marketplace 로 이 저장소를 등록한 1.x 사용자는 채널을
  `release/1.x` 로 고정한다 — `claude plugin marketplace add "ykylee/standard_ai_workflow#release/1.x"` (상세: 1.30.0 노트 §0).
- 발행 도구: 판 정렬이 PEP 440 (사전 판 < 정식 판), GitHub latest 는 원격 최고 판일 때만, `pyproject` 판 쓰기가 판 문자열
  전체를 바꾼다 (옛 정규식은 `2.0.0b1` 을 두 번 쓰면 `2.0.0b1b1` 을 만들었다).

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 346/346 · slash 346/346 · rc 0. 결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8 · mypy strict 0.
- 하네스 실측 (Linux): 4 하네스 부트스트랩 · 세션 시작 (§16.4), 테스트베드 실사용 (§16.6), `/setup.md` (§16.7),
  이 저장소 실제 등록 · 들여오기 (main-021). 결함은 되주입으로 검사가 잡는지 쟀다.
- 발행 호스트: Linux.

## 4. 알려진 한계 (감추지 않는다)

- **베타다** — 2.0 계약의 보장 기간은 아직 정하지 않았다. 허브 API · MCP 도구 이름 · 인자는 stable 전까지 바뀔 수 있다
  (바꾸면 G4 대로 경고 한 판 뒤 제거).
- **macOS · Windows 호스트와 대화형 실행은 실측 전**이다 (M-039 WBS-39.1 남은 몫, 발행 뒤).
- **이 저장소 자신은 아직 1.x 가 정본**이다 — 테스트베드 허브에 들여왔지만 표식 전환은 상시 허브 위치를 정한 뒤.
- arcturus 이전(WBS-39.3)은 2.0 뒤 (요구 R15.4).
- 허브는 loopback 이 기본이다 — 바깥 노출은 TLS 리버스 프록시 뒤에서 (`HUB_OPERATIONS.md` §3). 허브에 닿는 누구나
  프로젝트를 등록할 수 있다.
- **PyPI 업로드는 하지 않는다**(RELEASE.md §1 각주 0). 배포는 GitHub Releases 하나다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-21T22:53:50Z)_

- total wiki pages: **100**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
