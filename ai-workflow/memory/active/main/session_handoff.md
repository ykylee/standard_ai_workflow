# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-18 (48차 세션 — main-002 close: 롤오프 포인터 멱등·치유)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **48차 세션 — main-002 close: 롤오프 포인터가 실행마다 쌓이던 결함 (check 11→14 cases).** `wk rollover-baselines` 는 이관처 포인터(`- 그 이전 기준선은 … (이관 N건)`)를 **매 실행 새로 덧붙였다** — 47차에 6회 돌자 7줄 → 13줄이 됐고 그 자리는 매 세션 시작에 읽힌다. 결함은 둘이었다: `apply_rollover` 가 기존 포인터를 **걷지 않고 insert 만** 한 것, 그리고 건수가 누적이 아니라 **이번 이관분**(`moved_count`)이었던 것(파일엔 45건인데 handoff 는 '3건' 을 말했다). 수리: 포인터를 **먼저 전부 걷고 하나만 다시 넣는다** — 그래서 치유가 이관과 독립이고 **상한 이하에서도 쌓인 상태를 접는다**(`needs_pointer_fix` 신호 신설, 이 경우 `baselines.md` 는 안 건드린다). 건수의 정본은 `baselines.md` 로 옮겼다(`count_archived`). **case 4 가 "포인터가 있는가" 만 봐서 쌓는 구현이 11 cases 를 전부 통과했다** — 있는가는 사라지는 회귀만 잡고 쌓이는 회귀는 **개수를 세야** 잡힌다. case 12(연속 3회 실행 후 1줄)·13(상한 이하 치유)·14(건수 = 실제 항목 수) 신설, 되주입 2종 양방향 red 실증. 실물 사본에 47차 모양(12줄)을 재현해 `--apply` → 1줄·건수 갱신·나머지 무변경 확인.
- 직전 기준선: **47차 세션 종료 — 플러그인 설치 + 배포 축 gap 1·2 해소 + 결함 3건 (6 push, 전량 2축 매번 green, 검사 260→262).** 상세는 [47차 세션 기록](./sessions/plugin_install_and_deployment_probe_2026-08-18.md). 축은 **설치가 조사를 낳았다** 였다 — 플러그인을 깔아 보니 Codex 설치본이 버전은 같은데 내용만 낡아 있었고(`1.2.0` 동일), 그 한 줄이 세션 전체를 끌었다. ①**main-017**(직전 항목, 채널별 재실행 계약 4채널 실측). `INSTALLATION` **§7.0.2 신설** — 채널 × (설치본의 정체 / 설치 재실행 / update / 페이로드가 낡았을 때 복구). **계약이 채널마다 다르다**: claude-code = 캐시 사본이고 `plugin update` 가 **버전 문자열만 보고 거절**(복구는 `uninstall`→`install` 뿐) · codex = 캐시 사본이지만 `plugin add` 재실행이 marketplace 루트에서 **다시 복사**해 같은 버전에서도 갱신된다 · grok-build = 재설치 **거부**, `update` 는 `already live` 를 출력하면서 **실제로는 갱신 안 함**(원본에 표식을 넣어 확정) · pi-dev = `~/.pi/agent/settings.json` 의 `packages[]` **경로 참조**라 사본이 없고 갱신 자체가 불필요. gemini-cli 는 CLI 부재로 **미실측**(표에 명시). **claude 의 `marketplace update` 는 클론만 당기고 설치 캐시는 안 고친다** — 실측 중 설치본이 main-002 가 고친 잘린 줄을 그대로 들고 있었고 **버전은 양쪽 다 `1.2.0`** 이었다. 컨셉 §6: 원칙 B(재실행 안전)는 4채널 전부 성립, **원칙 C 는 플러그인 채널에서 깨진다**고 근거와 함께 명시. `check_installation_usage` case 5 신설(4→5) — 표가 §2.1 매트릭스의 플러그인 채널을 전부 덮는지 **파생으로** 검사(손 목록 없음), 되주입 red 실증. grok·pi 는 측정용 임시 설치 후 **원상복구 확인**.
- 그 이전 기준선: **47차 세션 (이어서) — AGENTS.md 공유 진입점 합류, 게이트에서 로컬 예외가 사라졌다 (전량 2축 262/262 green, park 없음).** 이 저장소의 Codex 진입점 자리를 oh-my-codex(OMX) 계약이 점유하고 `.gitignore` 로 추적에서 빠져 있어, (a) Codex 세션이 §1/§8/§11 을 못 받고 (b) `check_docs`·`check_self_application` 2건이 **로컬에서만** red 였다(CI 는 파일이 없어 green). 소유자 선택 3안 — 컨셉 §4.2 의 **공유 진입점 + additive rule**: OMX 계약이 master, 문서 끝에 `render_entrypoint_rules` 생성 블록 + 영문 metadata 6필드(첫 20줄), 실행 기본값·게이트 규칙은 `CLAUDE.md` 를 **가리키기만** 하고 복제하지 않았다. `.gitignore` 에서 `/AGENTS.md` 제거(`ANTIGRAVITY.md`·`GEMINI.md` 는 유지). **`omx setup` 재생성 위험**은 파일 안 blockquote 로 경고 + 복구 명령 명시 — 소실되면 `check_self_application` 이 즉시 red 라 조용히 사라지지 않는다. **부수 실증**: 새 날짜 index 로의 main-009 이월이 `carry_over_entry` 로 자동 처리됐다 — main-001 수리의 첫 실사용이고, 어제였으면 또 손 append 였다.
- 그 이전 기준선: **47차 세션 (이어서) — main-003 close: 죽어 있던 제외 목록 수리 (전량 2축 262/262 green).** `check_deprecation_3rd_cycle` 의 제외가 **경로 기준 불일치로 한 건도 성립하지 않았다** — `rel` 은 `REPO_ROOT` 상대인데 제외 항목(`build`/`.venv`/`tests`)은 `WORKFLOW_SOURCE` 기준이라 `workflow-source/.venv/...` 가 `.venv` 로 시작할 수가 없었다. 평소엔 그 디렉터리가 없어 아무도 몰랐고, 로컬에 있는 호스트에서만 site-packages 16건이 저장소 결함으로 보고됐다. 수리: 기준을 `WORKFLOW_SOURCE` 로 통일하고 `_iter_source_files` 하나로 모음 · 판정을 문자열 `startswith` → **경로 조각**(`buildtools/` 오인·중첩 `.venv` 누락 방지) · case 1 의 `endswith` 완화 제거(그 완화가 어긋남을 가리고 있었다). **case 4 신설(3→4)** — 합성 경로 7종 직접 판정 + 원 결함을 실행 가능한 단언으로 보존 + 제외 대상이 스캔에 새는지 관찰. cases 1~3 은 제외가 죽어도 조용히 green 이었다. **성과: 로컬 `workflow-source/.venv` 를 비켜 두지 않고 게이트가 돈다** — 세션 내내 하던 수작업 하나가 사라졌다.
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 46건, 최신이 위).

- 현재 주 작업 축: **배포 일관성·멱등성 — 1순위 gap(탐침)이 닫혔고 나머지 3건이 남았다.** 정본은 [`workflow_deployment_idempotency.md`](../../../../workflow-source/core/workflow_deployment_idempotency.md) (배포=함수, 변수 5축, 3계약+1탐침, 소유권 3분류, 멀티 하네스 공존·설치 스코프 규칙). **구현 순서**: ~~[main-016] `wk doctor`~~ ✅ · ~~[main-017] 채널 재실행 계약~~ ✅ (둘 다 47차) → **[main-018] 드리프트 감지 — 이제 1순위이자 근거가 확실하다**(마커가 같고 내용만 낡은 상태를 실제로 관측했고 채널이 스스로 못 고쳤다 → 마커가 아니라 **페이로드 해시** 비교) → [main-019] 환경 pre-flight. **release 경계 대기** — [TASK-2026-08-14-main-009] 라벨 영어 전환은 `TASK_FIELD_LABELS` 한 줄만 남았고 case 10 이 안전을 선실증. 45차에 구조 결함(main-005/006/010/011)과 판단 보류(main-004 = 기각)가 전부 닫혀 실행형 잔여는 배포 축뿐이다. **이 호스트 설치 현황(47차 실측)**: Claude Code ✅ user scope v1.2.0 (GitHub marketplace) · Codex ✅ v1.2.0 (로컬 `workflow-source/dist/plugins/codex/1.2.0/install-root`, **gitignore 대상이라 `dist/` 를 지우면 marketplace 가 끊긴다** — 재빌드는 `python3 -m workflow_kit.plugin_distribution --harness codex --output-dir workflow-source/dist`). **게이트의 로컬 유래 red 는 0건이다** (2026-08-18) — `AGENTS.md` 는 추적 전환 + 규칙 합류, `workflow-source/.venv` 는 main-003 수리로 해소. **전량을 돌릴 때 비켜 둘 파일이 없다.** **관찰** — [TASK-2026-08-13-main-004] mypy flake 33 run 연속 green(진행 중) / cross-host federation / darwin mavis e2e / memory_index 3-tuple 추이.
- ~~소유자 결정 대기: state.json 생성물 여부~~ — ✅ **해소** (TASK-018, 2026-08-11): **생성물로 확정.** 정본 §11.2 에 선언, `wk refresh-state` 로 재생성, `check_state_json_generated` case 5 가 이 저장소의 정합을 상시 검사. 상세 요약·산문은 state.json 이 아니라 handoff §4 와 task 파일(SSOT)에 남긴다.
- 다음 후보 축: ~~PyPI 발행~~ → ⛔ **닫힘 (2026-08-14 소유자 최종 결정 = 발행 안 함, `RELEASE.md` §1 각주 0)** / cross-host federation (두 번째 호스트 = **MacBook 확정, 시점 추후**) / memory_index 3-tuple 지표 추이 관찰. ~~federation self-host add~~ ✅ (14차) · ~~v1.1.9/v1.2.0 미발행 누적~~ ✅ **해소 (32차 — v1.2.0-beta 발행, 누적분 0)**. (v1.1.0·v1.1.1 노트 누적 표기는 TASK-014 에서 **미삽입 확정**, branch protection 은 소유자가 **보류 결정** (2026-08-11) — 둘 다 후보 축에서 제거.)
- 발견한 cross-project 패턴 (agent memory 추가):
  - **Federation pattern** (4 후보 검토: central ❌ / git ❌ / S3 ❌ / federation ✅)
  - **MCP/CLI dual mode** (operational tool 의 4종 wrapper)
  - **3-layer defense** (규약 + client hook + server protection)
  - **Scope drift detection** (3-way enum: planned_done / planned_undone / unplanned_done)
  - **time.mktime → calendar.timegm** (UTC timestamp KST 환경 함정)
  - **[project.scripts] entry points** (CLI 化 A안, venv e2e 검증)
  - **기존 dispatcher 확장 > 새 dispatcher** (진입점이 둘로 갈리면 `--help` 도 갈린다)
  - **serving 없는 pull 은 반쪽** (API 만 있고 부를 CLI 가 없으면 기능이 없는 것과 같다)
  - **모름 ≠ 안전** (검사에서 못 읽은 필드를 통과로 치면 거짓 안심을 준다)
- 최근 핵심 기준 문서:
  - [multi_workspace_orchestration.md](../../../../workflow-source/core/multi_workspace_orchestration.md) — **§0.7 상태표 + §7.1·§7.3 구현 표시** + §0.8 *아직 열려 있는 것* 4건
  - [global_workflow_standard.md §10](../../../../workflow-source/core/global_workflow_standard.md) — 다중 작업·협업 규칙
  - [MEMORY_GOVERNANCE.md](../../../../workflow-source/MEMORY_GOVERNANCE.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-18-main-002 rollover-baselines 가 실행마다 포인터 줄을 하나씩 쌓는다
- TASK-2026-08-14-main-017 채널별 재실행 계약 표 — 5개 플러그인 채널의 재설치/업데이트 시 행동을 §7.0 에 고정
- TASK-2026-08-18-main-001 AGENTS.md 를 공유 진입점으로 합친다 — oh-my-codex 계약과 워크플로우 규칙 공존
- TASK-2026-08-16-main-003 check_deprecation_3rd_cycle 의 제외 목록이 죽어 있다 — rel 기준과 제외 항목 기준이 어긋난다
- TASK-2026-08-16-main-001 backlog-update update 모드의 새 daily index 이월 결함 — 두 번째 task 부터 cannot_determine 조용한 스킵
- TASK-2026-08-14-main-016 wk doctor — post-apply 탐침: 스코프별 설치 현황·버전·로드 가능성·환경 전제 한 명령
- TASK-2026-08-16-main-002 정본 §11.2 다중 줄 bullet 이 추출에서 잘린다 — 생성 블록이 문장 중간에서 끊긴 채 전 하네스로 복제
- TASK-2026-08-14-main-015 배포 일관성·멱등성 컨셉 문서 — workflow_deployment_idempotency.md 신설
- TASK-2026-08-14-main-014 배포 패키지·배포 방식 정리 — 채널×하네스 매트릭스를 정본 문서에
- TASK-2026-08-14-main-013 RELEASE.md 현재 package version 동기화 — PR #26 을 main 직접 반영으로 대체
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

### ▶ 지금 할 일 — [main-018] 드리프트 감지 (47차에서 근거가 확정됨)

**마커가 같고 내용만 낡은 상태를 이 세션에 실제로 관측했고, 채널이 스스로 고치지
못한다는 것까지 확인됐다.** 그래서 비교 대상은 마커가 아니라 **페이로드 해시**여야
한다. 자리는 이미 표시돼 있다 — `wk doctor` 출력의 `drift.limitation`.

- 관측 1: Codex 설치본이 정본과 내용만 달랐다 (버전 양쪽 다 `1.2.0`).
- 관측 2: claude-code 설치 캐시가 `main-002` 가 고친 잘린 줄을 그대로 들고 있었고
  `plugin update` 가 **버전 문자열만 보고 거절**했다. `uninstall`→`install` 로만 고쳐졌다.
- 채널별 복구 절차는 `docs/INSTALLATION_AND_USAGE.md` §7.0.2 에 있다 (47차 실측).

이어서 [main-019] 환경 pre-flight. 상세는
[47차 세션 기록](./sessions/plugin_install_and_deployment_probe_2026-08-18.md).

### 47차가 남긴 규칙 (재발 방지)

- **`git stash` 는 워킹 트리 복원 수단이 아니다** — untracked 를 안 건드린다.
  이 세션에서 그것 때문에 "이전부터 red 였다" 고 **오판**했다. 로컬/CI 차이를
  볼 때는 **HEAD 클린 워크트리**로 잰다.
- **되주입은 fixture 가 실제로 판별하는지까지 확인한다** — `grok-buildX` 가
  `grok-build` 를 부분 문자열로 포함해 되주입이 통과한 일이 있었다.
- **검사를 하나 늘리면 개수 표기 3곳이 같이 움직인다** — INSTALLATION ·
  release note · smoke trend. 게이트가 잡아 주지만 미리 맞추면 한 바퀴를 아낀다.
- **게이트에 비켜 둘 로컬 파일은 이제 없다** (`AGENTS.md` 추적 전환 + main-003
  수리). 다시 park 가 필요해지면 그건 새 결함이다.

### 다음에 할 일 — 전량 검사 시간 (소유자 승인 2026-08-14)

"전량 검사가 매번 도는 게 진행을 더디게 한다" 는 지적에서 나왔다. 실측 결론:
**벽시계를 정하는 것은 255개가 아니라 8개다.** 그리고 **가장 큰 낭비는 도구가 아니라
사용 패턴이었다** — 이 세션에 전량 2축을 5번 돌렸는데 게이트로서 의미 있던 것은 1번뿐.

| | 1축 실측 (2026-08-14, 부하 있는 상태) |
|---|---|
| 벽시계 / CPU | 196s / 819s (255 checks) |
| 정숙 구간(직렬) | 61s — 그중 `no_repo_write` **39s (64%)** |
| 병렬 임계경로 | `wiki_score` **68s** 단독 |
| 1초 미만 | **160개** (개수는 비용이 아니다) |

- ✅ **즉시 적용**: `CLAUDE.md` 에 3단 규칙 명문화 — 편집 중 `--filter` / 커밋 전
  관련 검사 + `check_self_application` / **push 직전 1회만 2축 전량**.
- ① [TASK-2026-08-13-main-009] 무거운 8개 (임계경로 둘부터)
- ② [TASK-2026-08-14-main-003] `--changed` 선택 실행 (미선언은 항상 실행 + 스킵 출력)
- ③ [TASK-2026-08-14-main-004] 2축→1축 조건부 — **앞의 둘을 끝낸 뒤에.**
  절감은 가장 크지만 15연속 CI red 를 만든 그 비대칭이다. 안 하는 것도 결론이다.

### ⛔ 닫힌 안건 — PyPI 발행 안 함 (2026-08-14, 소유자 최종 결정)

**배포는 이 저장소의 GitHub Releases 하나로 간다.** 토큰·OIDC 운영 비용을 상시로 지는
대신 얻는 것이 지금 없고, 공개는 되돌릴 수 없는 2년 backward compat 약속을 낯선
소비자에게 지운다.

**이 안건을 다시 제안하지 않는다.** 기술 준비는 v1.2.0 에서 이미 끝나 있으므로("이제
올릴 수 있다") 제안이 계속 생길 자리다 — 그래서 결정과 함께 **재검토 트리거 3개**를
정본에 박아 두었다: [`docs/RELEASE.md` §1 **각주 0**](../../../../docs/RELEASE.md).
그 트리거(외부 사용자의 실제 요청 / 저장소 밖 배포 사유 / 소유자 지시)가 성립하기
전에는 열지 않는다.

- [TASK-2026-08-13-main-008] TestPyPI 리허설 → **취소**. 업로드는 실행되지 않았고
  앞으로도 하지 않는다. 업로드 직전까지의 실측 8종은 **이력으로 보존** — GitHub
  Releases 소비자에게도 유효한 검증이다(README 렌더링·메타데이터·이름 해석·라이선스
  동봉·진입점 등).
- `RELEASE.md` §1 의 **각주 1**(TestPyPI 1회 한정 허용, 2026-08-13)은 **만료**.
- 검토 문서 2건(`pypi-publication-policy-review` / `cli-distribution-review`)은
  **종결 표기** 후 근거 자료로만 남는다.

### 무엇이 끝났나 (2026-08-14, 37차 세션)

**브랜치 정리 — 36차 기능의 첫 자기 적용** (TASK-2026-08-14-main-001). 상세는
[세션 기록](./sessions/branch_cleanup_and_case7_false_positive_2026-08-14.md).

아래 36차의 종료 순서를 그대로 밟았고 **도구는 설계대로 동작했다**:
`origin/fix/archive-history-integrity` 삭제(고유 커밋 0, tip `f798947` 은 main 이력에 남음)
→ `wk archive-branch-memory --apply` 가 **이 handoff 의 세션 기록 링크 2건**과 아카이브된
`state.json` **5경로 전부**를 재작성했다. `.archived.json` 의 `open_task_ids` 는 `[]` 다.
`active/` 에 남은 브랜치 네임스페이스는 `main` 하나.

**종료 순서에 0번이 빠져 있었다.** 브랜치 task 가 `in_progress` 인 채였고(일은 끝났는데
파일이 안 따라왔다) 아카이브가 정당하게 막혔다. 아래 1번은 "이월" 만 말하고 **"내 일이
끝났으면 닫는다"** 를 안 말하고 있었다:

```bash
# 0) 내 브랜치 task 를 먼저 done 으로 마감한다 (완료 기준·작업 결과·검증 결과를 채워서)
#    --validation-result 가 없으면 backlog-update 가 done 을 in_progress 로 낮춘다
#    함정: --done-criteria / --result-note 는 반복해도 마지막 하나만 남는다 (append 아님)
```

**유령 ID 2건.** 이 handoff §4 와 36차 세션 기록이 가리키던
`TASK-2026-08-13-fix-…-001` 은 **존재한 적 없는 ID** 였다 (실재는 `…-08-14-…`) — 세션
기록의 `관련 문서` 링크는 태어날 때부터 죽어 있었고, §4 의 완료 기록은 어느 task 파일과도
연결되지 않았다. 호스트가 UTC 라 도구 기본 날짜는 `08-13`, 사람이 쓴 문장은 KST `08-14`
였다. 둘 다 실재 ID 로 교정.

**아카이브 직후 `check_archive_history_integrity` 가 red — 위양성이었다.** case 7 의 링크
정규식이 **자체 사본**이라 label 을 요구하지 않아(`](path "제목")` 형태), 링크 문법을
*설명하는* 산문을 링크로 오인했다. 하필 그 문서가 방금 아카이브한 세션 기록이다 —
**검사가 자기 세션의 기록을 못 견뎠다.** 문서를 고치지 않고 판정을
정본(`workflow_kit.common.markdown`)에 맞추고 사본을 걷었다. 위양성을 내는 검사는
무시당한다. case 14 를 **양방향**으로 새로 두었다 (예시 산문은 안 잡고, 진짜 깨진 링크는
잡는다) — case 7 은 살아 있는 저장소를 관찰할 뿐이라 "안 잡는" 쪽으로 무력화돼도 조용히
green 이기 때문이다. 되주입으로 실측 확인. 13 → 14 cases.

### 무엇이 끝났나 (2026-08-14, 36차 세션)

**브랜치 메모리 생애주기** (PR #25 병합). 상세는
[세션 기록](../../archived/fix/archive-history-integrity/sessions/archive_history_integrity_2026-08-13.md).

**브랜치 종료 순서** — 아카이브가 이제 미완료 task 를 막는다:

```bash
# 1) 미완료 task 를 먼저 처리한다 (이월했으면 원본에 carried_over_to: <새 ID>)
# 2) 브랜치 삭제 (아카이브는 '브랜치 부재' 를 종료 신호로 쓴다 — 역방향 점검)
git push origin --delete <branch> && git branch -D <branch>
wk archive-branch-memory --dry-run   # 막히면 어느 task 때문인지 알려준다
wk archive-branch-memory --apply     # 참조(링크·state.json)도 함께 재작성한다
```

막히면 우회하지 말고 이월한다. `archived/` 는 state 생성기도 dashboard 도 읽지
않으므로, 미완료인 채 넘어가면 그 작업은 어디에서도 안 보이게 된다.

### 무엇이 끝났나 (2026-08-13, 35차 세션)

**브랜치 메모리 네임스페이스 가드** (PR #24 병합). 상세는
[세션 기록](../../archived/fix/branch-memory-namespace-guard/sessions/branch_memory_namespace_guard_2026-08-13.md).

**브랜치를 파면 제일 먼저 이걸 돌린다** — 순서가 거꾸로면 절반짜리 네임스페이스가 되고
3검사가 red 다 (이번에 그 순서로 밟아 실측):

```bash
git checkout -b <branch>
wk seed-workspace-memory --branch <branch> --axis '<작업 축>' --task-title '<제목>' --apply
# ↑ 여기까지가 한 벌 — handoff + backlog + sessions + state.json 이 다 생긴다 (v1.2.1+)
wk backlog-update ... --mode update    # 이후 갱신
```

`wk backlog-update` 는 `backlog/` 만 만든다 (`tasks_dir.mkdir()` 의 부수효과).
`sessions/` 와 `session_handoff.md` 가 빠진다. 이제 `check_branch_memory_namespace` 가
커밋 전에 지목한다.

~~**미결로 남긴 것**: `fix/branch-memory-namespace-guard` 미아카이브~~ — ✅ **완료**
(`archived/fix/branch-memory-namespace-guard/`). 이제 `active/` 에 남은 브랜치
네임스페이스는 `main` 하나다.

### 무엇이 끝났나 (2026-08-10, 3차 세션)

**CI 재현성 회복 + smoke 병렬화** (TASK-016~019). 상세는
[세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md).
2차 세션(TASK-008~015, ADR-006 후속 + v1.1.6-beta 발행)은 §4 하단 항목 참조.

**push 전 재현 명령이 둘로 늘었다** — 둘 다 CLAUDE.md 에 적혀 있다:

```bash
# 브랜치 매트릭스 (CI 는 2축, 로컬 무인자는 1축 — 이 비대칭이 15연속 red 를 만들었다)
python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>

# SDK 매트릭스 (mcp 를 쓰는 코드를 건드렸으면)
PYTHONPATH=workflow-source python3 -m workflow_kit.common.sdk_matrix --run-local
```

전량 검사는 이제 **기본이 병렬**(`--jobs auto`)이다. 재현이 필요하면 `--jobs 1`.
저장소 전역을 관찰하는 검사를 새로 만들면 파일 안에 `REQUIRES_QUIET_REPO = True` 를
선언해야 한다 — 안 하면 병렬에서 오탐이 난다.

### 다음에 할 일 (순서)

이 세션에서 **저장소 리팩터링 조사**를 했고, 아래는 그 결과다 (근거는 §6 아래
"조사로 확정된 것" 참조). 사용자가 우선순위를 정한 항목만 실행했다 (정숙 구간 근본
수정 = TASK-019). 나머지는 미착수:

- ~~`check_mypy_strict_v0_11_3` ~ `v0_11_10` 8개 제거~~ — ✅ **완료**
  (TASK-2026-08-11-main-001, smoke 268→260).
- ~~`ai-workflow` 아카이브 정리~~ — ✅ **완료** (TASK-2026-08-11-main-003,
  185파일 제거, wiki 참조 1건 + freeze 최소 세트 6건 보존, README 링크 교정).
- ~~`check_cache_*` 13개 통합~~ — ✅ **완료** (TASK-2026-08-11-main-004,
  31 case verbatim 보존, smoke 260→248).
- ~~`release_pipeline.py` 분할~~ — ✅ **완료** (TASK-2026-08-11-main-007,
  3908→3174 + 모듈 4개, 분석 지도 방식). `dashboard_data.py` ✅ (TASK-010, 2488→1526),
  `workflow_kit_cli.py` ✅ (TASK-011, 2095→583) — **대형 파일 분할 완결**.
- ~~`docs/presentations/*.pdf|pptx` 5.2MB~~ — ✅ **완료** (TASK-2026-08-11-main-009, 파생 바이너리 제거·소스 보존).
- ~~branch protection~~ — **보류 결정** (2026-08-11, 소유자). `main` 미보호 (404 실측)
  상태를 인지한 채 일단 켜지 않기로 함. 재검토 시 `wk check-branch-protection` 으로
  현황 판정부터 (도구는 판정만 한다 — v1.1.2 §2.3).
- ~~`mooneye` 브랜치 처리~~ — ✅ **완료** (TASK-2026-08-11-main-012, `origin/mooneye`
  삭제. 고유 커밋 0 — 172 커밋 전부 main 에 존재, `active/mooneye/` 부재로
  memory 아카이브 해당 없음).

## 6. 남은 리스크 / 확인하지 못한 것

- ~~`cmd_release --apply` 실전 미검증~~ — ✅ **해소** (v1.1.4-beta 발행으로 apply
  경로 전체 실증: tag push / gh release / dashboard emit / audit append).
- **호스트 환경 의존 게이트** — 시스템 python 에는 mypy/mcp/twine 이 없어 관련 검사가
  fail 한다 (venv 에서 전부 PASS — `.venv` 에 dev,release,mcp-sdk 설치돼 있음).
  release 는 반드시 venv 에서 돌린다.
- ~~TST-WF-01 advisory red~~ — ✅ **해소** (TASK-004, 측정 재설계로 hard 복귀 +
  compliant). 남은 흔적: v0.15.18 dummy wrapper 는 측정에서 배제될 뿐 파일에
  남아 있다 — 물리 제거는 115 파일 churn 이라 별건.
- **darwin homelab 에서 mavis e2e 재확인 필요** — 검사를 정본 읽기로 바꿨으므로 mavis
  설치 호스트에서 한 번 돌려 기존과 동일하게 green 인지 확인하는 것이 안전하다.
- ~~title drift 임계 0.6 heuristic~~ — ✅ **해소** (TASK-008, 실측 캘리브레이션으로
  0.6 유지 확정 + `check_title_drift_calibration` 이 재캘리브레이션을 강제).
- ~~registry loopback 만 실측~~ — **부분 해소** (TASK-009, 비-loopback bind + pull
  왕복은 이 호스트에서 실측). **잔여**: 진짜 cross-host / 방화벽 / reverse proxy /
  TLS 종단 — 두 번째 호스트 필요 (darwin homelab).
- ~~`check_no_repo_write` 의 계약 한계~~ — ✅ **해소** (TASK-2026-08-12-main-009, 실행-중 폴링 + 원장). 이전 기술: 판정이 "실행 **후** 복원되었는가"
  라, 건드렸다 되돌리면 통과한다. `check_bidir_link_v0_13_3` 은 **이미 감시 목록에
  있었는데도** 그 이유로 안 잡혔다. 실행 *중* 감시(폴링)로 강화하면 남은 감시 대상
  다수가 같은 이유로 red 가 될 수 있어 범위가 크다. **되돌리는 것은 안 건드리는 것이
  아니다.**
- ~~amend Guard 2 의 staged-삭제 fatal~~ — ✅ **해소** (TASK-2026-08-11-main-002,
  `needs_add_only` 선별 + case 10 되주입으로 고정. §4 참조).
- **transient pyproject writer 정체 미상 (2026-08-11 1회 관측)** — 병렬 전량
  실행 중 원본 `pyproject.toml` 이 일시 변경됐다 되돌아왔다 (version_auto_sync
  byte-대조가 포착). 재현 실패 (표적 3회 + 전량 2회 + 50ms md5 watcher).
  관찰자 3검사는 정숙화(TASK-008)로 위양성 차단됨. **감시 수단은 저장소에
  고정됨** (TASK-013, `workflow-source/tools/watch_transient_writer.py` —
  일회용 `~/tmp` 스크립트의 승격판): 재발 의심 시 전량 검사 옆에 백그라운드로
  세워 두면 diff + ps 전량 + fuser 를 이벤트별로 남긴다 (로그는 temp 에만,
  저장소 안 로그는 거부). `check_watch_transient_writer` 5 case 가 되주입
  양방향으로 계약을 고정. `check_no_repo_write` 의 "실행 후 복원" 계약 한계와
  같은 뿌리로 추정 — writer 특정 자체는 재발 시의 일이다.
- **정숙 구간 6건** (TASK-008 로 3→6) — `check_no_repo_write`(전역 관찰) /
  `check_parallel_smoke`(runner 호출) / `check_source_without_runtime_layer`
  (저장소 복사) 는 본질적 직렬이고, `version_auto_sync` / `self_recovering` /
  `bidir_link` 는 원본 byte-대조 관찰 때문 (TASK-008). 병렬화로 더 줄이려면
  이들의 설계 자체를 바꿔야 한다.
- 이 밖의 과거 세션 리스크 (`--force` 3rd layer 미가동)는 변화 없음 —
  2026-08-09 까지의 세션 기록 참조.

## 7. 저장소 구성 조사 (2026-08-10 3차 세션)

리팩터링 판단 근거. git 추적 **1766 파일**:

| 영역 | 파일 | 비고 |
|---|---|---|
| `workflow-source` | 898 | tests 268, workflow_kit 129, releases 171, tools 74 |
| `ai-workflow` | 778 | **backlog tasks 193 + 아카이브 142**, wiki 81, sessions 18 |
| `docs` | 36 | presentations PDF/PPTX 가 **5.2MB** |

- **"버전 접미사 71개 = 중복" 은 틀렸다** (이 세션에서 정정). 주제별로 갈라보니
  대부분 고유하고, 진짜 중복은 `mypy_strict_v0_11_3~10` 8개뿐이다.
- 테스트가 느렸던 주된 원인은 **저장소 크기가 아니라 실행 방식**이었다 (순차 →
  병렬로 345s→118.8s). 위 정리 항목 중 실행 시간을 실제로 줄이는 것은 mypy 8개
  (15초) 뿐이고 나머지는 저장소 위생 문제다 — 섞어서 "정리하면 빨라진다" 고 말하지
  않는 편이 정확하다.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-09](./sessions/cli_dispatcher_and_rotation_2026-08-09.md) ·
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
