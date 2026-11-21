# Beta v1.30.0 (2026-11-21)

> **상태: 릴리스 준비.** package `1.30.0`, runtime `__version__ = 1.30.0`, tag `v1.30.0`.
> **1.x 안내 판 — 1.x 줄의 마지막 minor** (요구 R16.2 · R16.4, `release/1.x` 머리에서 발행). 2.0 워크플로우 허브
> (`v2.0.0b1`)와 같은 날 낸다. 이 뒤 1.x 는 **2028-07-20 까지 결함 수리 patch(`1.30.x`)만** 낸다.
>
> 등급 근거 (§1.5 · R16.2): v1.29.1 이후 코드 커밋 4 — feat 1 (안내 판), fix 3, breaking 0 — **minor**.
> 공개 Python API 시그니처 제거 0, 진입점 제거 0. 추가: 모듈 `workflow_kit.common.transition_notice` ·
> `workflow_kit.common.hub_marker`, 발행 도구 함수 `release_version_key` · `is_prerelease` · `release_latest_decision`.
> **동작이 바뀌는 곳**: ① `session-start` 성공 출력의 `summary` 끝에 안내 한 줄 ② 저장소에 '허브로 옮김' 표식
> (`ai-workflow/HUB_MIGRATED.json`)이 있으면 1.x 쓰기 명령이 종료 코드 3 으로 거절 ③ 발행 도구의 판 정렬이 PEP 440
> (사전 판 < 정식 판).

## 0. 2.0 · 전환 경로 · 1.x 끝 (R16.4 의 세 항목)

- **2.0** — 상태(task · handoff · 이력 · 로드맵 · 지침 · 위키)의 정본이 **워크플로우 허브**(서버 하나)에 있고, 작업
  환경은 kit 를 깔지 않고 허브 주소 하나로 참여한다. 하네스는 허브의 원격 MCP 로 붙는다. 첫 판 `v2.0.0b1`
  (`main` 브랜치) — 허브 운영은 2.0 의 `docs/HUB_OPERATIONS.md`.
- **전환 경로** — 저장소에서 에이전트에게 "`<허브 주소>/setup.md` 를 읽고 이 저장소를 셋업해" → 1.x 기록 들여오기
  `python3 .workflow-hub/hub_client.py migrate plan` → `migrate import <MIG> all` → '허브로 옮김' 표식 커밋. 표식이
  있는 저장소에서 이 판의 1.x 쓰기 명령은 거절되고 `session-start` 는 허브를 가리킨다. 표식을 지우면 1.x 로 돌아온다.
- **1.x 끝(EOL) = 2028-07-20** (stable_guarantee 의 보장 끝, R16.3). 그날부터 `session-start` 의 안내 한 줄이 EOL 을
  말한다 — 막지 않고 종료 코드도 그대로다.
- **1.x 에 머물려면** 플러그인 채널을 `release/1.x` 에 고정한다 — 2.0(`main`)은 같은 이름의 kit 플러그인 채널을 내지
  않는다 (R16.6). Claude Code: `claude plugin marketplace remove standard-ai-workflow` →
  `claude plugin marketplace add "ykylee/standard_ai_workflow#release/1.x"` → `claude plugin install
  standard-ai-workflow@standard-ai-workflow` (2026-11-21 실측 — 설치 판이 `release/1.x` 를 따른다. remove 는 그
  플러그인의 저장된 옵션 · 데이터도 지운다). 로컬 clone 소스 채널은 그 clone 을 `release/1.x` 로. 상세: README §0.

## 1. 릴리스 요약

- 범위: `v1.29.1..` **4 commits** — feat 1 (`12c5d96f`), fix 3 (`072d62c3` · `7530b195` · `f1ed96ca`) (+ 발행 준비 1).
- 누적 smoke **336/336 PASS** (로컬 `--branch-context=all` = 336 × native/slash).
- 검사 파일 수 333 → 336 (`check_hub_marker_1x` · `check_transition_notice` · `check_release_prerelease_latest`).
- 2.0 줄(`main`)과의 관계 (R16.5): 표식 거절 · 잠금 수리 · 발행 도구 수리는 main 에도 같다. 안내 한 줄 · README §0 은
  1.x 에만 (2.0 해당 없음).

## 2. 소비자에게 보이는 변화

### 2.1 `session-start` 의 안내 한 줄 (`12c5d96f`, R14.8 · R16.3)

- 성공 출력의 `summary` 마지막 줄 — EOL 전: `[2.0] 워크플로우 허브(2.0)가 나왔다 — 이 1.x 줄은 2028-07-20 까지 결함
  수리만 한다. …`, 그날부터: `[EOL] 1.x 줄은 2028-07-20 에 끝났다 — …`.
- `warnings` 에는 넣지 않는다 — 권장 다음 행동이 '경고 해결' 로 바뀌지 않는다. 종료 코드 · `status` 그대로.

### 2.2 '허브로 옮김' 표식 거절 (`072d62c3`, R14.6 · R14.7)

- 저장소 뿌리 위쪽에서 `ai-workflow/HUB_MIGRATED.json` 을 찾으면, 메모리 · 계획 · 위키 · 목적을 쓰는 명령(22개 —
  `hub_marker.GUARDED_COMMANDS`)이 종료 코드 3 · `error_code: hub_migrated` · 허브 주소로 거절하고 저장소를 바꾸지 않는다.
  MCP 의 계획 응답 반영도 같다. `session-start` 는 아무것도 쓰지 않고 허브를 가리킨 뒤 종료 코드 0.

### 2.3 발행 도구 (`f1ed96ca`, R16.7)

- 판 정렬이 PEP 440 — 사전 판(`2.0.0b1` · 옛 `-beta`)이 같은 숫자의 정식 판보다 앞선다 (옛 정렬은 반대였고 `0b1` 을 버렸다).
- `gh release create` 는 원격 태그 가운데 이 판이 가장 높을 때만 `--latest`, 아니면 `--latest=false` — 2.x 가 나온 뒤
  1.x patch 는 latest 를 가져가지 않는다. `--target` 은 현재 브랜치 (전에는 `main` 고정).

### 2.4 검사 러너 잠금 파일 (`7530b195`)

- `run_all_checks` 잠금 파일의 보유자 정보가 `a+b` 모드에서 앞에 덧붙어 깨지던 것 → `r+b`.

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 336/336 · slash 336/336 · rc 0. 결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8.
- 새 검사: `check_transition_notice` 3 cases (되주입 4 — 당일 경계 · 요약에서 빠짐 · warnings 에 들어감 · 날짜 오류에 죽음), `check_hub_marker_1x` 6 cases, `check_release_prerelease_latest` 5 cases (되주입 4).
- 발행 호스트: Linux.

## 4. 알려진 한계 (감추지 않는다)

- **채널 고정은 사용자가 한다** — 고정하지 않은 Claude Code marketplace(GitHub 원격)는 2.0 발행 뒤 `main` 에 marketplace
  가 없어 갱신이 실패한다 (설치된 1.x 는 그대로 돈다). 고정 명령은 위 §0.
- 안내 한 줄은 이 판 이상의 kit 에서만 보인다 — kit 를 올리지 않은 저장소는 2.0 을 모른다.
- Codex 의 1.x 채널은 버전이 박힌 zip 이라 자동 갱신이 원래 없다 — 이 판의 zip 을 다시 깔아야 안내가 보인다.
- **Windows 실측은 이번 판에도 없다** (M-028/WBS-28.3).
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.
