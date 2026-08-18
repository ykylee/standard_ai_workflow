# 세션 기록 — 47차: 플러그인 설치 + 배포 축 gap 1·2 해소 + 결함 3건 (2026-08-16 ~ 08-18)

- 문서 목적: 47차 세션의 작업 축과 결정을 다음 세션이 이어받을 수 있게 남긴다.
- 범위: 플러그인 2채널 설치, 결함 3건 수리(main-002/001/003), `wk doctor` 신설(main-016), 채널 재실행 계약 실측(main-017), AGENTS.md 공유 진입점 합류
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-18
- 관련 문서: [handoff](../session_handoff.md), [backlog](../backlog/2026-08-18.md), [컨셉 문서](../../../../../workflow-source/core/workflow_deployment_idempotency.md), [INSTALLATION §7.0.1·§7.0.2](../../../../../docs/INSTALLATION_AND_USAGE.md)

## 0. 한 줄 요약

플러그인을 이 호스트에 깔아 보는 것으로 시작해, **깔린 것을 확인할 방법이 없다**는
사실을 밟았고, 그것이 배포 축 gap 1(탐침)·2(재실행 계약)의 해소로 이어졌다.
커밋 6건, 전량 2축은 매번 green, 검사 260 → 262.

## 1. 설치가 조사를 낳았다

Claude Code 플러그인은 미설치였고 Codex 는 이미 설치돼 있었다. 그런데 Codex 쪽
**페이로드가 낡아 있었다** — 버전 문자열은 `1.2.0` 으로 정본과 같은데 내용만
구버전(KO 단일 description, `rollover-baselines` 항목 누락)이었다.

**버전 비교로는 안 걸리는 드리프트.** 이 한 줄이 이 세션 전체의 축이 됐다.

## 2. main-002 — 정본의 다중 줄 bullet 이 첫 줄에서 잘렸다

Codex 재빌드 산출물을 diff 하다가 드러났다. `standard_rules.parse_standard` 가
`- ` 로 시작하는 줄만 모으고 **들여쓴 연속 줄을 잇지 않아**, 정본 §11.2 의 3줄
bullet 이 잘린 채 스냅샷 → 진입점 → 하네스 산출물 7곳으로 복제돼 있었다.

**하필 잘려나간 쪽이 실제 지시문이었다** (`wk rollover-baselines` 를 쓰라는 명령과
"손으로 지우지 말라" 는 금지). 남은 문장은 아무 행동도 지시하지 않았고, **아무
검사도 red 가 아니었다.**

- `_collect_bullets` 헬퍼로 연속 줄 join. §1 principles 와 §11.2 parse_contract 가
  같은 헬퍼를 쓴다 — 둘은 원래도 같은 결함을 공유했고 §1 이 전부 한 줄이라 안
  드러났을 뿐이다.
- `check_standard_single_source` case 10 (9→10). 되주입 + **옛 알고리즘이면 꼬리를
  잃는지까지** 단언 — 없으면 case 자신이 죽어도 조용히 green 이다.

## 3. 게이트 판독 — 첫 전량 9 red, 코드 결함 0건

| 원인 | 건수 | 정체 |
|---|---|---|
| `.venv` 개발 의존성 부재 | 6 | uv venv 에 pip 조차 없었다 (`ensurepip` 로 복구) |
| 로컬 untracked `AGENTS.md` | 2 | `.gitignore` 대상, oh-my-codex 파일 |
| 로컬 `workflow-source/.venv` | 1 | 검사가 site-packages 를 저장소 코드로 스캔 |

**CI 는 셋 다 없어 green** — SDK 매트릭스·브랜치 매트릭스에 이은 세 번째
"로컬/CI 비대칭" 이다.

**판단 오류 1건**: `git stash` 로 "이전부터 red 였다" 고 봤는데 틀렸다. stash 는
untracked 를 안 건드려 `AGENTS.md` 가 그대로 남아 있었다. HEAD 클린 워크트리로
재확인해 교정했다. **stash 는 워킹 트리 복원 수단이 아니다.**

## 4. main-016 — `wk doctor` (배포 gap 1)

`workflow_kit/deploy_doctor.py`. `probe(project_root, home)` → environment /
project_scope / global_scope / drift 4절. **둘 다 주입 인자**라 fixture 로 검증되고
실 홈을 읽지 않는다. report-only, 기본 rc 0, `--strict` 만 rc 1.

**첫 실행이 설계 결함 둘을 바로 드러냈다:**

1. **존재는 적용이 아니다.** 마커 없는 `AGENTS.md` 하나가 codex·grok-build·
   minimax-code·opencode·pi-dev **5개 하네스를 적용됨으로** 만들었다. kit 소유
   표식(마커, 컨셉 §3)이 있는 것만 `applied`, 존재만 하는 쪽은 `candidate` 로 분리.
2. **기준이 없으면 드리프트 절이 통째로 죽는다.** `ai-workflow/VERSION` 은 플러그인
   채널과 소스 저장소에 없다. 돌고 있는 패키지 버전으로 폴백하고 출처를 밝히게
   하자마자 **실제 드리프트**를 지목했다 — 이 저장소 자신의 claude-code 산출물이
   `v1.0.0-beta` (kit 1.2.0).

`check_deploy_doctor` 9 cases. report-only 는 트리 지문 대조로 고정하되 **지문
자신이 쓰기를 구분하는지**까지 확인한다.

## 5. main-001 — 날짜 롤오버 이월 결함

daily index 는 *그날 손댄 목록* 이고 SSOT 는 `tasks/<id>.md` 인데, update 경로가
"오늘 index 에 없으면 `cannot_determine`" 으로 끝나 **날짜가 바뀐 순간부터 진행 중
task 의 갱신이 무시**됐다. 그러고도 최상위 `status` 는 `ok` 였다.

2회 연속 세션에서 밟았고 두 번째에는 조용히 끝나지 않았다 — linter
`task_status_mismatch` → `check_self_application` red 로 **커밋 게이트를 세웠다**.
그 결함을 task 파일에 기록하려던 호출 자신도 같은 이유로 스킵됐다.

**막고 있던 것은 판정 한 줄이었다.** 병합(`update_merge` 는 `matched_task` 가 아니라
`task_ssot_path.exists()` 를 본다)과 index append 는 원래부터 맞았다.

- SSOT 가 있으면 미지의 ID 가 아니라 **이월** → `carry_over_entry`.
- **`cannot_determine` 의 최상위 `status` 를 `ok` → `warning`.** 조용한 미반영의
  뿌리는 판정이 아니라 이 보고였다.
- `check_backlog_carry_over` 5 cases (반대 방향 포함 — 같은 날 재갱신은 여전히
  `update_entry`). 되주입에서 4건 red.

수리된 도구가 자기 자신의 close 를 `carry_over_entry` 로 처리했다.

## 6. main-003 — 죽어 있던 제외 목록

`check_deprecation_3rd_cycle` 의 제외가 **한 건도 성립하지 않았다.** 경로는
`REPO_ROOT` 기준인데 제외 항목은 `WORKFLOW_SOURCE` 기준이라 `workflow-source/.venv/…`
가 `.venv` 로 시작할 수가 없었다.

- 기준을 `WORKFLOW_SOURCE` 로 통일하고 `_iter_source_files` 하나로 모음.
- 판정을 `startswith` → **경로 조각** (`buildtools/` 오인·중첩 `.venv` 누락 방지).
- case 1 의 `endswith` 완화 제거 — 그 완화가 어긋남을 가리고 있었다.
- **case 4 신설**: cases 1~3 은 제외가 죽어도 조용히 green 이었다(대상 디렉터리가
  평소엔 없다). 합성 경로 7종으로 규칙 자체를 판정.

## 7. AGENTS.md — 공유 진입점 합류 (소유자 선택 3안)

Codex 진입점 자리를 oh-my-codex 계약이 점유하고 `.gitignore` 로 빠져 있어, (a) 이
저장소의 Codex 세션이 §1/§8/§11 을 못 받고 (b) 검사 2건이 로컬에서만 red 였다.

컨셉 §4.2 의 **공유 진입점 + additive rule**: OMX 계약이 master, 문서 끝에
`render_entrypoint_rules()` 생성 블록 + 영문 metadata 6필드. 실행 기본값·게이트
규칙은 `CLAUDE.md` 를 **가리키기만** 한다. `.gitignore` 에서 제거.

**`omx setup` 재생성 위험**은 파일 안 blockquote 로 경고 + 복구 명령. 소실되면
`check_self_application` 이 즉시 red 라 조용히 사라지지 않는다.

이 시점부터 **전량 검사에 비켜 둘 파일이 없어졌다.**

## 8. main-017 — 채널별 재실행 계약 4채널 실측 (배포 gap 2)

`INSTALLATION` **§7.0.2** 신설. 계약이 채널마다 다르다:

| 채널 | 설치본 | 설치 재실행 | update | 낡았을 때 복구 |
|---|---|---|---|---|
| claude-code | 캐시 사본 | no-op | **버전 문자열만 보고 거절** | `uninstall`→`install` **뿐** |
| codex | 캐시 사본 | **캐시를 다시 복사** | (Git 소스 전용) | `plugin add` 재실행 |
| grok-build | 사본 | **거부** | `already live` 출력하나 **갱신 안 함** | `uninstall`→`install` |
| pi-dev | **경로 참조** | 멱등 | 성공 | **불필요** |
| gemini-cli | 미실측 (CLI 부재) | | | |

**`marketplace update` 는 설치본을 안 고친다** (claude-code). 실측 중 설치 캐시가
main-002 가 고친 잘린 줄을 그대로 들고 있었고 **버전은 양쪽 다 `1.2.0`** 이었다.
`plugin update` 는 끝까지 거절했고 `uninstall`→`install` 로만 고쳐졌다.

컨셉 §6: 원칙 B(재실행 안전)는 4채널 전부 성립. **원칙 C(깔린 것은 스스로 말한다)는
플러그인 채널에서 깨진다** — 근거와 함께 명시했다.

`check_installation_usage` case 5 (4→5): 표가 §2.1 매트릭스의 플러그인 채널을
전부 덮는지 **파생으로** 검사. grok·pi 는 측정용 임시 설치 후 원상복구 확인.

## 9. 이 세션이 남긴 규칙

- **stash 는 워킹 트리 복원 수단이 아니다** — untracked 를 안 건드린다. 로컬/CI
  차이를 볼 때는 **HEAD 클린 워크트리**로 잰다.
- **되주입은 fixture 가 실제로 판별하는지까지 확인한다** — 이번에 `grok-buildX` 가
  `grok-build` 를 부분 문자열로 포함해 되주입이 통과한 일이 있었다.
- **"버전이 같으면 내용도 같다" 는 배포에서 성립하지 않는다** — 채널이 그 전제로
  업데이트를 거절한다.
- 검사를 하나 늘리면 개수 표기 3곳(INSTALLATION · release note · smoke trend)이
  같이 움직인다. 게이트가 잡아 주지만 미리 맞추면 한 바퀴를 아낀다.

## 10. 다음 세션 시작 포인트

**[TASK-2026-08-14-main-018] 드리프트 감지가 1순위이고 근거가 확실하다.** 마커가
같고 내용만 낡은 상태를 **실제로 관측**했고, 채널이 스스로 못 고친다는 것까지
확인됐다. 마커가 아니라 **페이로드 해시** 비교여야 한다 — `wk doctor` 의
`drift.limitation` 이 그 자리를 이미 표시해 두었다.

이어서 [main-019] 환경 pre-flight. 열린 잔여는
[TASK-2026-08-14-main-009] (release 경계 대기, `TASK_FIELD_LABELS` 한 줄) 와
gemini-cli 채널 미실측이다.
